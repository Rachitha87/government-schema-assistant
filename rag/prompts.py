"""
Prompts used by the response agents.

Design rule for this project: the LLM is a *writer*, not a *fact source*.
Everything it is allowed to state is handed to it inside <scheme> blocks that
come straight from the knowledge base. If those blocks are empty, the only
correct answer is "I do not have that information".
"""

from __future__ import annotations

from typing import Iterable, Optional

from models.profile import UserProfile
from models.scheme import Scheme
from utils.normalize import format_income

GROUNDING_RULES = """STRICT RULES (do not break these):
1. Use ONLY the facts inside the <scheme> blocks provided in the CONTEXT. Nothing else.
2. Never invent or guess eligibility criteria, benefits, deadlines, income limits or application links.
3. Never mention a scheme that is not present in the CONTEXT, and never add a URL that is not listed there.
4. If the CONTEXT does not contain enough information to answer, say so plainly and tell the user what is missing.
5. If a field says "not recorded in the knowledge base" or "not specified", say that it is not recorded here and point the user to the official portal.
6. The dataset is SAMPLE data. Always add a short line telling the user to verify details on the official government portal.
7. Keep the tone practical and respectful. Use short paragraphs or bullet points. No tables. No invented statistics.
8. Answer in the same language as the user's question (the app is English-first, so default to simple English)."""

CHAT_SYSTEM_PROMPT = f"""You are the "Scheme Response Agent" of the Government Scheme Assistant, an assistant that helps Indian students find government scholarships and welfare schemes.

Your job: answer the user's question using the retrieved knowledge-base context only.

{GROUNDING_RULES}

Output format:
- A short direct answer (2-5 sentences or a few bullets).
- One line per recommended scheme in the form: <scheme name> - <why it matches> (<deadline as given in context>) - <application link as given in context>.
- A final line: "Verify the details on the official portal before applying."

Do not output the tags <scheme>, <context> or any internal notes."""

RECOMMENDATION_SYSTEM_PROMPT = f"""You are the "Recommendation Agent" of the Government Scheme Assistant.

You receive an applicant profile and a set of eligibility-checked schemes from a knowledge base.

{GROUNDING_RULES}

Output format (plain text, no markdown tables):
- One short opening line: what the user appears to be eligible for, and what is still missing from their profile if anything.
- One block per recommended scheme:
  <scheme name> (<scheme id>)
  Why: <one sentence tied to the profile>
  Benefits: <exactly as in context>
  Deadline: <exactly as in context>
  Apply: <exactly as in context>
- Close with: "Please confirm every detail on the official government portal before applying."

Never add a scheme that is not in the context. If no scheme is eligible, say exactly that and mention near-misses only if they are present in the context."""


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------
def format_scheme_block(scheme: Scheme, eligibility_note: Optional[str] = None) -> str:
    """Render one scheme as a compact, unambiguous fact block."""
    lines = [
        f"<scheme id=\"{scheme.scheme_id}\">",
        f"Name: {scheme.name}",
        f"Provider: {scheme.provider}",
        f"Description: {scheme.description}",
        f"Eligibility: {scheme.eligibility}",
        f"Income limit: {scheme.income_limit}",
        f"Education level: {scheme.education_level}",
        f"Benefits: {scheme.benefits}",
        f"Deadline: {scheme.deadline}",
        f"Application link: {scheme.application_link or 'not recorded in the knowledge base'}",
        f"Data status: {scheme.data_status}",
    ]
    if eligibility_note:
        lines.append(f"Rule-engine result: {eligibility_note}")
    if scheme.notes:
        lines.append(f"Data note: {scheme.notes}")
    lines.append("</scheme>")
    return "\n".join(lines)


def build_context(schemes: Iterable[Scheme], notes: Optional[dict[str, str]] = None) -> str:
    notes = notes or {}
    blocks = [
        format_scheme_block(scheme, notes.get(scheme.scheme_id))
        for scheme in schemes
    ]
    return "\n\n".join(blocks)


def build_chat_messages(
    question: str,
    schemes: Iterable[Scheme],
    profile: Optional[UserProfile] = None,
    history: Optional[list] = None,
    notes: Optional[dict[str, str]] = None,
) -> list[dict[str, str]]:
    """Assemble the full message list sent to the LLM."""
    scheme_list = list(schemes)
    profile_block = "No profile information available yet."
    if profile and any(value is not None for value in profile.model_dump().values()):
        profile_block = (
            f"Applicant: {profile.summary()}.\n"
            f"Missing fields: {', '.join(profile.missing_fields()) or 'none'}"
        )

    if scheme_list:
        context = build_context(scheme_list, notes)
    else:
        context = (
            "<scheme>No scheme in the knowledge base matched this request.</scheme>"
        )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"<profile>\n{profile_block}\n</profile>\n\n"
                f"<context>\n{context}\n</context>\n\n"
                f"<question>\n{question}\n</question>"
            ),
        },
    ]

    for message in history or []:
        role = getattr(message, "role", None) or message.get("role")
        content = getattr(message, "content", None) or message.get("content")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": str(content)})

    return messages


def build_recommendation_messages(
    profile: UserProfile,
    schemes: Iterable[Scheme],
    notes: Optional[dict[str, str]] = None,
) -> list[dict[str, str]]:
    """Assemble the messages for the recommendation flow."""
    scheme_list = list(schemes)
    context = build_context(scheme_list, notes) if scheme_list else (
        "<scheme>No scheme in the knowledge base is eligible for this profile.</scheme>"
    )
    user_block = (
        f"<profile>\n"
        f"Name: {profile.name or 'not provided'}\n"
        f"Age: {profile.age if profile.age is not None else 'not provided'}\n"
        f"Gender: {profile.gender or 'not provided'}\n"
        f"State: {profile.state or 'not provided'}\n"
        f"Category: {profile.category or 'not provided'}\n"
        f"Family income: {format_income(profile.family_income)}\n"
        f"Education level: {profile.education_level or 'not provided'}\n"
        f"Course: {profile.course or 'not provided'}\n"
        f"Student status: {profile.student_status or 'not provided'}\n"
        f"Disability: {profile.disability_status or 'not provided'}\n"
        f"Missing fields: {', '.join(profile.missing_fields()) or 'none'}\n"
        f"</profile>"
    )
    return [
        {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"{user_block}\n\n<context>\n{context}\n</context>",
        },
    ]


def build_insufficient_context_message(topic: str = "this request") -> str:
    """The safe answer when nothing relevant was retrieved."""
    return (
        f"I could not find any scheme in the knowledge base that matches {topic}, "
        "so I do not want to guess.\n\n"
        "You can try:\n"
        "- adding your state, category, income and education level in the Profile page,\n"
        "- browsing the full scheme list under Browse Schemes,\n"
        "- checking the official National Scholarship Portal (https://scholarships.gov.in).\n\n"
        "This assistant answers only from its sample dataset - always confirm the current "
        "eligibility and deadline on the official government portal."
    )
