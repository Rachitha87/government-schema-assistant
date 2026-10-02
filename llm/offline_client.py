"""
Offline (no-LLM) provider.

Why this exists: the project must run end-to-end on a fresh machine even before
anyone has an API key. This client reads the same `<scheme>` context blocks that
are given to a real LLM and assembles a factual answer from them.

Consequences:
  * The app always returns a usable answer (never a 500 because of a missing key).
  * The answer is guaranteed to be grounded - every sentence comes from the
    knowledge base.
  * `used_llm` is reported as False so the UI can label the response honestly.
"""

from __future__ import annotations

import re
from typing import Optional

from llm.base import BaseLLMClient, LLMResponse

SCHEME_BLOCK_RE = re.compile(
    r'<scheme id="(?P<id>[^"]+)">(?P<body>.*?)</scheme>', re.DOTALL
)
FIELD_RE = re.compile(r"^(?P<key>[A-Za-z ]+):\s*(?P<value>.*)$")
QUESTION_RE = re.compile(r"<question>\s*(?P<body>.*?)\s*</question>", re.DOTALL)

DISCLAIMER_LINE = (
    "This is sample data for demonstration - verify eligibility, benefits and "
    "deadlines on the official government portal before applying."
)


class OfflineClient(BaseLLMClient):
    """Deterministic, retrieval-only answer generator."""

    name = "offline"
    model = "rule-based-template"

    @property
    def available(self) -> bool:
        return True

    # -- context parsing -------------------------------------------------
    @staticmethod
    def _parse_schemes(text: str) -> list[dict[str, str]]:
        schemes: list[dict[str, str]] = []
        for match in SCHEME_BLOCK_RE.finditer(text):
            fields: dict[str, str] = {"scheme_id": match.group("id")}
            for line in match.group("body").splitlines():
                field_match = FIELD_RE.match(line.strip())
                if field_match:
                    key = field_match.group("key").strip().lower()
                    fields[key] = field_match.group("value").strip()
            schemes.append(fields)
        return schemes

    @staticmethod
    def _parse_question(text: str) -> str:
        match = QUESTION_RE.search(text)
        if match:
            return match.group("body").strip()
        return ""

    # -- answer composition ----------------------------------------------
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        last_user_message = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                last_user_message = message.get("content", "")
                break

        schemes = self._parse_schemes(last_user_message)
        question = self._parse_question(last_user_message)

        if not schemes:
            answer = (
                "I could not find a matching scheme in the sample knowledge base, "
                "so I will not guess.\n\n"
                "Please add your state, category, family income and education level "
                "in the Profile page, or browse the full list under Browse Schemes. "
                "The official National Scholarship Portal is https://scholarships.gov.in\n\n"
                + DISCLAIMER_LINE
            )
            return LLMResponse(text=answer, provider=self.name, model=self.model, used_llm=False)

        lines: list[str] = []
        # The question itself is not echoed: the grounding check compares every
        # amount/date/URL in the answer against the knowledge base, and the
        # user's own income is not scheme data.
        lines.append("Based on the sample knowledge base, here is what applies to your request.")
        lines.append("")

        for index, scheme in enumerate(schemes, start=1):
            name = scheme.get("name", "Untitled scheme")
            scheme_id = scheme.get("scheme_id", "?")
            lines.append(f"{index}. {name} ({scheme_id})")
            if scheme.get("provider"):
                lines.append(f"   Provider: {scheme['provider']}")
            if scheme.get("eligibility"):
                lines.append(f"   Eligibility: {scheme['eligibility']}")
            if scheme.get("benefits"):
                lines.append(f"   Benefits: {scheme['benefits']}")
            if scheme.get("deadline"):
                lines.append(f"   Deadline: {scheme['deadline']}")
            link = scheme.get("application link", "")
            lines.append(
                f"   Apply: {link}" if link and "not recorded" not in link.lower()
                else "   Apply: link not recorded in the knowledge base - check the official portal"
            )
            if scheme.get("rule-engine result"):
                lines.append(f"   Match: {scheme['rule-engine result']}")
            lines.append("")

        lines.append(DISCLAIMER_LINE)
        lines.append(
            "Note: this response was generated without an LLM key (retrieval-only mode). "
            "Set GROK_API_KEY in your .env file to enable AI-written answers."
        )

        return LLMResponse(
            text="\n".join(lines).strip(),
            provider=self.name,
            model=self.model,
            used_llm=False,
        )
