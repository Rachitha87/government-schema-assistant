"""
Grounding / hallucination guard-rails.

The LLM is only ever allowed to speak about schemes that were retrieved from
the knowledge base. This module re-checks the generated text and removes or
flags anything that does not appear in the retrieved source material:

  * URLs that are not in the knowledge base are replaced with a placeholder.
  * Rupee amounts and dates are compared against the retrieved scheme text.

It is intentionally a *defence in depth* step, not a substitute for the
prompt. It is deterministic and easy to explain in an interview.
"""

from __future__ import annotations

import re
from typing import Iterable

from models.scheme import Scheme
from utils.normalize import _UNITS  # noqa: F401  (kept for the unit table)

URL_RE = re.compile(r"https?://[^\s)\]\"'<>]+", re.IGNORECASE)

MONEY_RE = re.compile(
    r"(?:₹|rs\.?|inr)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(crore|crores|lakh|lakhs)?",
    re.IGNORECASE,
)
LAKH_RE = re.compile(
    r"\b([0-9][0-9,]*(?:\.[0-9]+)?)\s*(crore|crores|lakh|lakhs)\b", re.IGNORECASE
)

NUM_DATE_RE = re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b")

TEXT_DATE_RE = re.compile(
    r"\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4})\b",
    re.IGNORECASE,
)

MONTHS = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "sept": "09", "oct": "10", "nov": "11",
    "dec": "12",
}

REMOVED_URL_PLACEHOLDER = "[link withheld: not present in the knowledge base]"


def _normalise_url(url: str) -> str:
    cleaned = url.rstrip(".,;:")
    return cleaned if cleaned.lower().startswith("http") else f"https://{cleaned}"


def _allowed_links(schemes: Iterable[Scheme]) -> set[str]:
    allowed: set[str] = set()
    for scheme in schemes:
        link = (scheme.application_link or "").strip()
        if link:
            allowed.add(_normalise_url(link))
    return allowed


def _money_to_rupees(amount: str, unit: str | None) -> float:
    try:
        value = float(str(amount).replace(",", ""))
    except ValueError:
        return -1.0
    return value * _UNITS.get((unit or "").lower(), 1)


def _allowed_money(schemes: Iterable[Scheme]) -> set[float]:
    """Every rupee amount that appears in the retrieved scheme text."""
    allowed: set[float] = set()
    for scheme in schemes:
        haystack = " ".join(
            [scheme.benefits, scheme.income_limit, scheme.description, scheme.eligibility]
        )
        for match in MONEY_RE.finditer(haystack):
            allowed.add(_money_to_rupees(match.group(1), match.group(2)))
        for match in LAKH_RE.finditer(haystack):
            allowed.add(_money_to_rupees(match.group(1), match.group(2)))
    return {value for value in allowed if value >= 0}


def _allowed_dates(schemes: Iterable[Scheme]) -> set[str]:
    """Normalised dates that appear in the retrieved scheme text."""
    allowed: set[str] = set()
    for scheme in schemes:
        haystack = " ".join([scheme.deadline, scheme.notes])
        for match in NUM_DATE_RE.finditer(haystack):
            allowed.add(_canon_date(match.group(0)))
        for match in TEXT_DATE_RE.finditer(haystack):
            allowed.add(_canon_text_date(match.group(1)))
    return {value for value in allowed if value}


def _canon_date(value: str) -> str:
    parts = re.split(r"[-/]", value)
    if len(parts) != 3:
        return value
    day, month, year = parts
    if len(year) == 2:
        year = "20" + year
    return f"{int(day):02d}-{int(month):02d}-{year}"


def _canon_text_date(value: str) -> str:
    match = re.match(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", value.strip(), re.IGNORECASE)
    if not match:
        return value
    month = MONTHS.get(match.group(2)[:4].lower()) or MONTHS.get(match.group(2)[:3].lower())
    if not month:
        return value
    return f"{int(match.group(1)):02d}-{month}-{match.group(3)}"


def check_grounding(
    answer: str,
    schemes: Iterable[Scheme],
    extra_allowed_money: Iterable[float] = (),
) -> tuple[str, list[str]]:
    """
    Verify the generated answer against the retrieved schemes.

    Args:
        answer:  the generated text.
        schemes: the schemes that were retrieved (the only permitted source).
        extra_allowed_money: additional legitimate amounts, e.g. the applicant's
            own family income, which the answer may quote back to them.

    Returns:
        (cleaned_answer, warnings)

    Any warning means the answer contained a fact that is not backed by the
    knowledge base, and the UI shows it to the user.
    """
    warnings: list[str] = []
    scheme_list = list(schemes)
    if not scheme_list:
        # Nothing retrieved -> nothing may be claimed as a fact.
        return answer, warnings

    allowed_links = _allowed_links(scheme_list)
    allowed_money = _allowed_money(scheme_list)
    allowed_money.update(float(value) for value in extra_allowed_money if value)
    allowed_dates = _allowed_dates(scheme_list)

    def _url_sub(match: re.Match[str]) -> str:
        url = _normalise_url(match.group(0))
        if url in allowed_links:
            return url
        warnings.append(f"Removed link that is not in the knowledge base: {url}")
        return REMOVED_URL_PLACEHOLDER

    cleaned = URL_RE.sub(_url_sub, answer)

    for match in set(MONEY_RE.findall(cleaned)):
        amount = _money_to_rupees(match[0], match[1] if len(match) > 1 else None)
        if amount >= 0 and allowed_money and amount not in allowed_money:
            warnings.append(
                f"Rupee amount {match[0]}{' ' + match[1] if len(match) > 1 and match[1] else ''} "
                "is not present in the retrieved scheme text."
            )

    for match in set(LAKH_RE.findall(cleaned)):
        amount = _money_to_rupees(match[0], match[1] if len(match) > 1 else None)
        if amount >= 0 and allowed_money and amount not in allowed_money:
            warnings.append(
                f"Amount '{match[0]} {match[1] if len(match) > 1 and match[1] else ''}' "
                "is not present in the retrieved scheme text."
            )

    for match in set(NUM_DATE_RE.findall(cleaned)):
        if _canon_date(match) not in allowed_dates:
            warnings.append(f"Date '{match}' is not present in the retrieved scheme text.")

    for match in set(TEXT_DATE_RE.findall(cleaned)):
        if _canon_text_date(match) not in allowed_dates:
            warnings.append(f"Date '{match}' is not present in the retrieved scheme text.")

    return cleaned, warnings


if __name__ == "__main__":
    # Quick manual test -- run `python -m utils.grounding` to sanity check
    from rag.loader import get_scheme_store

    sample = get_scheme_store().get("SCH004")
    assert sample is not None, "knowledge base could not be loaded"

    good = (
        "AICTE Pragati Scholarship for Girls. Benefits: Rs. 50,000 per year. "
        f"Apply: {sample.application_link}. Deadline: 31-10-2026."
    )
    cleaned, issues = check_grounding(good, [sample])
    print("good answer  ->", issues or "no warnings (expected)")
    assert not issues, "the grounded answer must not raise warnings"

    bad = (
        "You can also get Rs. 5,00,000 from https://fake-portal.example.com/apply "
        "before 31-12-2026."
    )
    cleaned, issues = check_grounding(bad, [sample])
    print("bad answer   ->", len(issues), "warning(s) (expected 3):")
    for issue in issues:
        print("   -", issue)
    assert len(issues) == 3, f"expected 3 warnings, got {len(issues)}"
    print("\nGrounding check behaves as expected.")
