from datetime import datetime, timedelta, timezone

import pytest

from app.llm.context_builder import (
    MAX_CONTEXT_MESSAGES,
    SYSTEM_INSTRUCTION,
    ConversationContext,
    build_conversation_context,
)
from app.models.domain import Message

UTC = timezone.utc
BASE_TIME = datetime(2026, 2, 8, 14, 30, tzinfo=UTC)


def make_message(
    *,
    message_id: str,
    sender_name: str = "Sarah",
    sender_id: str = "sarah",
    type: str = "user",
    content: str = "Hello",
    minutes_offset: int = 0,
    status: str = "complete",
) -> Message:
    return Message(
        id=message_id,
        sender_id=sender_id,
        sender_name=sender_name,
        type=type,
        content=content,
        created_at=BASE_TIME + timedelta(minutes=minutes_offset),
        status=status,
    )


def test_empty_input_returns_system_instruction_only() -> None:
    context = build_conversation_context([])

    assert context.system_instruction == SYSTEM_INSTRUCTION
    assert context.conversation_history == ""
    assert context.full_prompt == SYSTEM_INSTRUCTION


def test_single_user_message_formatting() -> None:
    message = make_message(
        message_id="msg-1",
        sender_name="Sarah",
        content="We need to decide on a caching strategy.",
    )

    context = build_conversation_context([message])

    assert context.conversation_history == (
        "[2026-02-08 14:30] Sarah: We need to decide on a caching strategy."
    )


def test_mixed_conversation_matches_example_format() -> None:
    messages = [
        make_message(
            message_id="msg-1",
            sender_name="Sarah",
            content="We need to decide on a caching strategy.",
            minutes_offset=0,
        ),
        make_message(
            message_id="msg-2",
            sender_id="mike",
            sender_name="Mike",
            content="Redis seems good, but I am worried about cost.",
            minutes_offset=1,
        ),
        make_message(
            message_id="msg-3",
            sender_id="lisa",
            sender_name="Lisa",
            content="We are already heavily using GCP.",
            minutes_offset=2,
        ),
    ]

    context = build_conversation_context(messages)

    assert context.conversation_history.splitlines() == [
        "[2026-02-08 14:30] Sarah: We need to decide on a caching strategy.",
        "[2026-02-08 14:31] Mike: Redis seems good, but I am worried about cost.",
        "[2026-02-08 14:32] Lisa: We are already heavily using GCP.",
    ]


def test_ai_messages_use_gemini_label() -> None:
    messages = [
        make_message(
            message_id="msg-1",
            sender_name="Sarah",
            content="What do you think?",
            minutes_offset=0,
        ),
        make_message(
            message_id="msg-2",
            sender_id="gemini",
            sender_name="Sarah",
            type="ai",
            content="Given your GCP usage, Memorystore for Redis could simplify ops.",
            minutes_offset=3,
        ),
    ]

    context = build_conversation_context(messages)

    assert "[2026-02-08 14:33] Gemini: Given your GCP usage" in context.conversation_history


def test_system_messages_use_system_label() -> None:
    message = make_message(
        message_id="msg-1",
        type="system",
        sender_name="System",
        content="Room created.",
    )

    context = build_conversation_context([message])

    assert context.conversation_history == "[2026-02-08 14:30] System: Room created."


def test_messages_are_sorted_chronologically() -> None:
    messages = [
        make_message(message_id="msg-2", sender_name="Mike", content="Second", minutes_offset=5),
        make_message(message_id="msg-1", sender_name="Sarah", content="First", minutes_offset=1),
    ]

    context = build_conversation_context(messages)

    assert context.conversation_history.splitlines()[0].endswith("Sarah: First")
    assert context.conversation_history.splitlines()[1].endswith("Mike: Second")


def test_limits_to_last_thirty_messages() -> None:
    messages = [
        make_message(
            message_id=f"msg-{index}",
            sender_name="Sarah",
            content=f"Message {index}",
            minutes_offset=index,
        )
        for index in range(40)
    ]

    context = build_conversation_context(messages)
    lines = context.conversation_history.splitlines()

    assert len(lines) == MAX_CONTEXT_MESSAGES
    assert lines[0] == "[2026-02-08 14:40] Sarah: Message 10"
    assert lines[-1] == "[2026-02-08 15:09] Sarah: Message 39"


def test_skips_streaming_messages() -> None:
    messages = [
        make_message(
            message_id="msg-1",
            sender_name="Sarah",
            content="Complete message",
            minutes_offset=0,
        ),
        make_message(
            message_id="msg-2",
            type="ai",
            content="Partial response",
            minutes_offset=1,
            status="streaming",
        ),
    ]

    context = build_conversation_context(messages)

    assert context.conversation_history == "[2026-02-08 14:30] Sarah: Complete message"


def test_skips_blank_content() -> None:
    messages = [
        make_message(message_id="msg-1", content="   "),
        make_message(message_id="msg-2", content="Visible message", minutes_offset=1),
    ]

    context = build_conversation_context(messages)

    assert context.conversation_history == "[2026-02-08 14:31] Sarah: Visible message"


def test_full_prompt_combines_system_instruction_and_history() -> None:
    message = make_message(message_id="msg-1", content="Hello team")

    context = build_conversation_context([message])

    assert context.full_prompt.startswith(SYSTEM_INSTRUCTION)
    assert context.full_prompt.endswith("[2026-02-08 14:30] Sarah: Hello team")


def test_includes_error_status_ai_messages_with_content() -> None:
    message = make_message(
        message_id="msg-1",
        type="ai",
        content="I encountered an issue generating a full response.",
        status="error",
    )

    context = build_conversation_context([message])

    assert context.conversation_history == (
        "[2026-02-08 14:30] Gemini: I encountered an issue generating a full response."
    )


def test_naive_datetime_is_treated_as_utc() -> None:
    message = Message(
        id="msg-1",
        sender_id="sarah",
        sender_name="Sarah",
        type="user",
        content="Hello",
        created_at=datetime(2026, 2, 8, 14, 30),
        status="complete",
    )

    context = build_conversation_context([message])

    assert context.conversation_history.startswith("[2026-02-08 14:30]")
