import re
from dataclasses import dataclass
from typing import Literal

AI_MENTION_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])@(Gemini|AI)(?=$|\s|[.,!?;:)\]]|[\"'])",
    re.IGNORECASE,
)

AiMentionTrigger = Literal["Gemini", "AI"]


@dataclass(frozen=True)
class AiMention:
    trigger: AiMentionTrigger


def detect_ai_mention(content: str) -> AiMention | None:
    match = AI_MENTION_PATTERN.search(content)
    if match is None:
        return None

    trigger = match.group(1)
    if trigger.lower() == "gemini":
        return AiMention(trigger="Gemini")
    return AiMention(trigger="AI")


def contains_ai_mention(content: str) -> bool:
    return detect_ai_mention(content) is not None
