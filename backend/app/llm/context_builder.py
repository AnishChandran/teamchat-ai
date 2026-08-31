from dataclasses import dataclass
from datetime import timezone

from app.models.domain import Message

MAX_CONTEXT_MESSAGES = 30

SYSTEM_INSTRUCTION = """You are Gemini, an AI assistant participating in a collaborative team chat.

This is a multi-user team conversation. Multiple people are participating in the same room.
Read the transcript carefully and understand who said what.
You may address participants by name when it helps clarity.
Provide practical, concise, and actionable help based on the conversation context."""


@dataclass(frozen=True)
class ConversationContext:
    system_instruction: str
    conversation_history: str

    @property
    def full_prompt(self) -> str:
        if not self.conversation_history:
            return self.system_instruction
        return f"{self.system_instruction}\n\n{self.conversation_history}"


def build_conversation_context(messages: list[Message]) -> ConversationContext:
    eligible_messages = _select_messages(messages)
    lines = [_format_message(message) for message in eligible_messages]
    return ConversationContext(
        system_instruction=SYSTEM_INSTRUCTION,
        conversation_history="\n".join(lines),
    )


def _select_messages(messages: list[Message]) -> list[Message]:
    eligible = [
        message
        for message in messages
        if message.status != "streaming" and message.content.strip()
    ]
    eligible.sort(key=lambda message: message.created_at)
    if len(eligible) <= MAX_CONTEXT_MESSAGES:
        return eligible
    return eligible[-MAX_CONTEXT_MESSAGES:]


def _format_message(message: Message) -> str:
    timestamp = _format_timestamp(message.created_at)
    speaker = _speaker_label(message)
    return f"[{timestamp}] {speaker}: {message.content.strip()}"


def _format_timestamp(created_at) -> str:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    else:
        created_at = created_at.astimezone(timezone.utc)
    return created_at.strftime("%Y-%m-%d %H:%M")


def _speaker_label(message: Message) -> str:
    if message.type == "ai":
        return "Gemini"
    if message.type == "system":
        return "System"
    return message.sender_name
