"""
Deterministic eligibility engine.

IMPORTANT DESIGN DECISION
-------------------------
This module never calls an LLM. Eligibility is a rule problem, not a language
problem, so it is solved with exact comparisons against the structured fields
stored alongside every scheme. The LLM only rewrites the result in friendly
language - it can never decide that somebody is eligible.

Every check returns one of:
    True  -> criterion satisfied
    False -> criterion failed (reason is explained to the user)
    None  -> not enough information in the profile to evaluate this criterion
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from models.api import EligibilityCheck
from models.profile import UserProfile
from models.scheme import Scheme
from utils.normalize import education_matches, format_income

ELIGIBLE = "eligible"
NOT_ELIGIBLE = "not_eligible"
INSUFFICIENT = "insufficient_data"

#: Soft checks do not block eligibility - they only appear in the reason text
#: when the applicant has not provided the value.
SOFT_CRITERIA = {"academic_percentage"}


@dataclass
class EvaluationResult:
    """Outcome of evaluating one scheme against one profile."""

    scheme_id: str
    verdict: str
    reason: str
    score: float = 0.0
    checks: list[EligibilityCheck] = field(default_factory=list)
    failed_criteria: list[str] = field(default_factory=list)
    matched_criteria: list[str] = field(default_factory=list)
    unknown_criteria: list[str] = field(default_factory=list)

    @property
    def is_eligible(self) -> bool:
        return self.verdict == ELIGIBLE

    @property
    def is_near_miss(self) -> bool:
        """Eligible on everything the user told us, but one criterion failed."""
        return self.verdict == NOT_ELIGIBLE and len(self.failed_criteria) == 1

    @property
    def needs_more_info(self) -> bool:
        """A mandatory rule could not be verified from the profile."""
        return self.verdict == INSUFFICIENT


def _check(name: str, passed: Optional[bool], detail: str, hard: bool = True) -> EligibilityCheck:
    return EligibilityCheck(criterion=name, passed=passed, detail=detail, hard=hard)


def _course_key(value: str) -> str:
    """Lower-case, alphanumeric only - so "B.Tech" == "b tech" == "btech"."""
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _course_matches(course: Optional[str], keywords: list[str]) -> Optional[bool]:
    if not keywords:
        return None
    if not course:
        return None
    course_text = _course_key(course)
    for keyword in keywords:
        keyword_text = _course_key(keyword)
        if not keyword_text:
            continue
        if keyword_text in course_text or course_text in keyword_text:
            return True
    return False


def evaluate_scheme(scheme: Scheme, profile: UserProfile) -> EvaluationResult:
    """Evaluate a single scheme against a single profile."""
    checks: list[EligibilityCheck] = []

    # ---- Age ------------------------------------------------------------
    if profile.age is not None and (scheme.min_age is not None or scheme.max_age is not None):
        minimum = scheme.min_age or 0
        maximum = scheme.max_age or 200
        within = minimum <= profile.age <= maximum
        checks.append(
            _check(
                "age",
                within,
                f"Age {profile.age} vs scheme range {minimum}-{maximum} years",
            )
        )

    # ---- Family income ---------------------------------------------------
    if profile.family_income is not None and scheme.max_annual_income is not None:
        within = profile.family_income <= scheme.max_annual_income
        checks.append(
            _check(
                "family_income",
                within,
                f"Family income {format_income(profile.family_income)} vs ceiling "
                f"{format_income(scheme.max_annual_income)}",
            )
        )

    # ---- Category --------------------------------------------------------
    if scheme.categories and "All" not in scheme.categories:
        if profile.category:
            allowed = [item for item in scheme.categories]
            checks.append(
                _check(
                    "category",
                    profile.category in allowed,
                    f"Category {profile.category} vs eligible categories {', '.join(allowed)}",
                )
            )
        else:
            # Mandatory rule that we cannot verify -> do not claim eligibility.
            checks.append(
                _check(
                    "category",
                    None,
                    f"Scheme is only for {', '.join(scheme.categories)}; the applicant's "
                    "category is unknown",
                )
            )

    # ---- State -----------------------------------------------------------
    if scheme.states and "All" not in scheme.states:
        if profile.state:
            allowed = [item for item in scheme.states]
            within = any(
                profile.state.strip().lower() == item.strip().lower() for item in allowed
            )
            checks.append(
                _check(
                    "state",
                    within,
                    f"Scheme is limited to {', '.join(allowed)}; user is in {profile.state}",
                )
            )
        else:
            checks.append(
                _check(
                    "state",
                    None,
                    f"Scheme is limited to {', '.join(scheme.states)}; the applicant's "
                    "state is unknown",
                )
            )

    # ---- Gender ----------------------------------------------------------
    if profile.gender and scheme.gender and scheme.gender.lower() != "all":
        within = profile.gender.lower() == scheme.gender.lower()
        checks.append(
            _check("gender", within, f"Scheme is for {scheme.gender} applicants")
        )

    # ---- Education level -------------------------------------------------
    if profile.education_level:
        within = education_matches(profile.education_level, scheme.education_levels)
        checks.append(
            _check(
                "education_level",
                within,
                f"Education level {profile.education_level} vs required "
                f"{', '.join(scheme.education_levels) or 'Any'}",
            )
        )

    # ---- Course / discipline --------------------------------------------
    course_result = _course_matches(profile.course, scheme.course_keywords)
    if course_result is not None:
        checks.append(
            _check(
                "course",
                course_result,
                f"Course '{profile.course}' vs approved courses "
                f"{', '.join(scheme.course_keywords)}",
            )
        )

    # ---- Student status ---------------------------------------------------
    if (
        profile.student_status
        and scheme.student_status
        and scheme.student_status.lower() not in {"any", ""}
    ):
        within = profile.student_status.lower() == scheme.student_status.lower()
        checks.append(
            _check(
                "student_status",
                within,
                f"Scheme expects a {scheme.student_status} applicant",
            )
        )

    # ---- Disability -------------------------------------------------------
    if scheme.disability_required:
        within = profile.has_disability()
        detail = (
            "Scheme is reserved for persons with disability"
            if not within
            else "Applicant has declared a disability"
        )
        if profile.disability_status is None:
            checks.append(
                _check(
                    "disability_status",
                    None,
                    "This scheme is for persons with disability; disability status not provided",
                )
            )
        else:
            checks.append(_check("disability_status", within, detail))

    # ---- Academic percentage ---------------------------------------------
    if scheme.min_percentage is not None:
        if profile.academic_percentage is not None:
            checks.append(
                _check(
                    "academic_percentage",
                    profile.academic_percentage >= scheme.min_percentage,
                    f"Percentage {profile.academic_percentage}% vs required "
                    f"{scheme.min_percentage}%",
                    hard=False,  # soft: never blocks, only qualifies
                )
            )
        else:
            checks.append(
                _check(
                    "academic_percentage",
                    None,
                    f"Scheme prefers at least {scheme.min_percentage}%; the applicant's "
                    "percentage is unknown",
                    hard=False,
                )
            )

    # ---- Verdict ----------------------------------------------------------
    failed = [check.criterion for check in checks if check.passed is False]
    passed = [check.criterion for check in checks if check.passed is True]
    unknown = [check.criterion for check in checks if check.passed is None]
    unknown_hard = [
        check.criterion
        for check in checks
        if check.passed is None and check.criterion not in SOFT_CRITERIA
    ]

    if failed:
        verdict = NOT_ELIGIBLE
        reason = "Does not meet: " + ", ".join(failed)
    elif unknown_hard:
        # A mandatory rule could not be verified, so eligibility is unconfirmed.
        verdict = INSUFFICIENT
        reason = (
            "Matches what is known, but needs your "
            + ", ".join(unknown_hard)
            + " to confirm eligibility"
        )
    elif passed:
        verdict = ELIGIBLE
        reason = f"Meets all {len(passed)} applicable criteria: " + ", ".join(passed)
        if unknown:
            reason += f"; could not verify {', '.join(unknown)} (not mandatory)"
    else:
        verdict = INSUFFICIENT
        reason = "Not enough profile information to evaluate this scheme"

    # Ranking score: how well the profile matched, weighted by specificity.
    score = 0.0
    if passed or failed:
        score = len(passed) / max(len(passed) + len(failed), 1)
    if verdict == INSUFFICIENT:
        # Still rankable, but below anything that is fully confirmed.
        score *= 0.5
    # A scheme that matches on more criteria is ranked higher.
    score += min(len(passed), 6) * 0.05

    return EvaluationResult(
        scheme_id=scheme.scheme_id,
        verdict=verdict,
        reason=reason,
        score=round(score, 4),
        checks=checks,
        failed_criteria=failed,
        matched_criteria=passed,
        unknown_criteria=unknown,
    )


def evaluate_all(
    schemes: list[Scheme], profile: UserProfile
) -> list[EvaluationResult]:
    """Evaluate a list of schemes (used by the recommendation flow)."""
    return [evaluate_scheme(scheme, profile) for scheme in schemes]


def summarise(results: list[EvaluationResult]) -> dict:
    """Small counts object, handy for logs and the UI."""
    return {
        "evaluated": len(results),
        "eligible": sum(1 for item in results if item.verdict == ELIGIBLE),
        "not_eligible": sum(1 for item in results if item.verdict == NOT_ELIGIBLE),
        "insufficient_data": sum(1 for item in results if item.verdict == INSUFFICIENT),
    }


if __name__ == "__main__":
    # Quick manual test -- run `python -m utils.eligibility` to sanity check
    from rag.loader import get_scheme_store

    store = get_scheme_store()
    pragati = store.get("SCH004")          # girls, technical, income <= 8 lakh
    karnataka_obc = store.get("SCH013")     # OBC + Karnataka only

    girl = UserProfile(age=19, gender="Female", state="Kerala", category="OBC",
                       family_income=300000, education_level="Undergraduate",
                       course="B.Tech", student_status="Full-time")

    for scheme in (pragati, karnataka_obc):
        if scheme is None:
            continue
        result = evaluate_scheme(scheme, girl)
        print(f"{scheme.scheme_id} {scheme.name}")
        print(f"  verdict : {result.verdict}")
        print(f"  reason  : {result.reason}")
        for check in result.checks:
            mark = {True: "PASS", False: "FAIL", None: "N/A "}[check.passed]
            print(f"    [{mark}] {check.criterion}: {check.detail}")
        print()

    unknown_category = UserProfile(age=21, state="Karnataka", family_income=200000,
                                   education_level="Postgraduate", course="MCA")
    result = evaluate_scheme(karnataka_obc, unknown_category)
    print(f"Category not given -> {result.verdict}: {result.reason}")
    print(f"Counts: {summarise(evaluate_all(store.all(), girl))}")
