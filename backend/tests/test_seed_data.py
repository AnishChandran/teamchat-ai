import sys
from pathlib import Path

import pytest

SCRIPTS_ROOT = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

from seed_data import (  # noqa: E402
    ACME_ORG,
    DEFAULT_SEED_PASSWORD,
    GLOBEX_ORG,
    SEED_ORGANIZATIONS,
    all_seed_emails,
)


def test_seed_includes_two_organizations() -> None:
    assert len(SEED_ORGANIZATIONS) == 2
    assert [org.slug for org in SEED_ORGANIZATIONS] == ["acme", "globex"]


def test_each_organization_has_three_users_and_two_rooms() -> None:
    for org in SEED_ORGANIZATIONS:
        assert len(org.users) == 3
        assert len(org.rooms) == 2
        assert {room.id for room in org.rooms} == {"general", "engineering"}


def test_each_organization_has_one_admin() -> None:
    for org in SEED_ORGANIZATIONS:
        admins = [user for user in org.users if user.role == "admin"]
        assert len(admins) == 1


def test_room_membership_covers_all_users() -> None:
    for org in SEED_ORGANIZATIONS:
        user_ids = {user.id for user in org.users}
        for room in org.rooms:
            message_senders = {message.sender_id for message in room.messages}
            assert message_senders.issubset(user_ids)


def test_each_room_has_realistic_message_history() -> None:
    for org in SEED_ORGANIZATIONS:
        for room in org.rooms:
            assert len(room.messages) >= 10
            message_ids = [message.id for message in room.messages]
            assert len(message_ids) == len(set(message_ids))


def test_seed_emails_are_unique() -> None:
    emails = all_seed_emails()
    assert len(emails) == 6
    assert len(set(emails)) == 6


def test_acme_and_globex_user_names() -> None:
    assert [user.name for user in ACME_ORG.users] == ["Sarah", "Mike", "Lisa"]
    assert [user.name for user in GLOBEX_ORG.users] == ["John", "Jane", "Bob"]


def test_default_seed_password_is_documented_dev_default() -> None:
    assert DEFAULT_SEED_PASSWORD == "TeamChatDev123!"
