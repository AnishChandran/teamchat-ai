#!/usr/bin/env python3
"""Seed Firestore and Firebase Auth with deterministic local development data."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from firebase_admin import auth
from firebase_admin.auth import UserNotFoundError
from google.cloud import firestore

from app.core.firebase import get_firebase_app
from app.core.firestore import get_firestore_client
from seed_data import (
    DEFAULT_SEED_PASSWORD,
    SEED_ORGANIZATIONS,
    SeedOrganization,
    message_created_at,
    all_seed_emails,
)


@dataclass
class SeedStats:
    organizations_created: int = 0
    organizations_updated: int = 0
    auth_users_created: int = 0
    auth_users_updated: int = 0
    firestore_users_created: int = 0
    firestore_users_updated: int = 0
    rooms_created: int = 0
    rooms_updated: int = 0
    messages_created: int = 0
    messages_updated: int = 0
    actions: list[str] = field(default_factory=list)


def get_seed_password() -> str:
    return os.environ.get("SEED_USER_PASSWORD", DEFAULT_SEED_PASSWORD)


def delete_collection(
    collection_ref: firestore.CollectionReference,
    *,
    batch_size: int = 100,
    dry_run: bool,
) -> int:
    deleted = 0
    while True:
        docs = list(collection_ref.limit(batch_size).stream())
        if not docs:
            break
        if not dry_run:
            batch = collection_ref._client.batch()
            for doc in docs:
                batch.delete(doc.reference)
            batch.commit()
        deleted += len(docs)
    return deleted


def delete_organization_data(
    client: firestore.Client,
    organization_id: str,
    *,
    dry_run: bool,
) -> None:
    org_ref = client.collection("organizations").document(organization_id)

    for room_doc in org_ref.collection("rooms").stream():
        delete_collection(room_doc.reference.collection("messages"), dry_run=dry_run)

    delete_collection(org_ref.collection("rooms"), dry_run=dry_run)
    delete_collection(org_ref.collection("users"), dry_run=dry_run)

    if dry_run:
        print(f"[dry-run] would delete organization document {organization_id}")
        return

    org_ref.delete()


def reset_seed_data(*, dry_run: bool) -> None:
    client = get_firestore_client()
    for organization in SEED_ORGANIZATIONS:
        delete_organization_data(client, organization.id, dry_run=dry_run)

    for email in all_seed_emails():
        try:
            user = auth.get_user_by_email(email)
        except UserNotFoundError:
            continue
        if dry_run:
            print(f"[dry-run] would delete auth user {email}")
            continue
        auth.delete_user(user.uid)
        print(f"Deleted auth user {email}")


def upsert_auth_user(
    *,
    email: str,
    name: str,
    password: str,
    organization_id: str,
    user_id: str,
    dry_run: bool,
    stats: SeedStats,
) -> str | None:
    if dry_run:
        stats.actions.append(f"auth upsert {email} -> org {organization_id}")
        return f"dry-run-{email}"

    try:
        existing = auth.get_user_by_email(email)
        auth.update_user(
            existing.uid,
            password=password,
            display_name=name,
            email=email,
        )
        firebase_uid = existing.uid
        stats.auth_users_updated += 1
        stats.actions.append(f"updated auth user {email}")
    except UserNotFoundError:
        created = auth.create_user(
            email=email,
            password=password,
            display_name=name,
        )
        firebase_uid = created.uid
        stats.auth_users_created += 1
        stats.actions.append(f"created auth user {email}")

    auth.set_custom_user_claims(
        firebase_uid,
        {"organizationId": organization_id, "userId": user_id},
    )
    return firebase_uid


def upsert_organization(
    client: firestore.Client,
    organization: SeedOrganization,
    *,
    dry_run: bool,
    stats: SeedStats,
) -> None:
    org_ref = client.collection("organizations").document(organization.id)
    org_snapshot = org_ref.get()
    org_data = {
        "name": organization.name,
        "slug": organization.slug,
        "createdAt": message_created_at(0),
    }

    if dry_run:
        action = "update" if org_snapshot.exists else "create"
        stats.actions.append(f"{action} organization {organization.slug}")
        if not org_snapshot.exists:
            stats.organizations_created += 1
        else:
            stats.organizations_updated += 1
    else:
        if org_snapshot.exists:
            org_ref.set(org_data, merge=True)
            stats.organizations_updated += 1
            stats.actions.append(f"updated organization {organization.slug}")
        else:
            org_ref.set(org_data)
            stats.organizations_created += 1
            stats.actions.append(f"created organization {organization.slug}")

    user_ids = [user.id for user in organization.users]
    firebase_uids: dict[str, str] = {}
    password = get_seed_password()

    for user in organization.users:
        firebase_uid = upsert_auth_user(
            email=user.email,
            name=user.name,
            password=password,
            organization_id=organization.id,
            user_id=user.id,
            dry_run=dry_run,
            stats=stats,
        )
        if firebase_uid is None:
            continue
        firebase_uids[user.id] = firebase_uid

        user_ref = org_ref.collection("users").document(user.id)
        user_data = {
            "firebaseUid": firebase_uid,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "createdAt": message_created_at(0),
        }

        if dry_run:
            action = "update" if user_ref.get().exists else "create"
            stats.actions.append(f"{action} firestore user {organization.slug}/{user.id}")
            if action == "create":
                stats.firestore_users_created += 1
            else:
                stats.firestore_users_updated += 1
            continue

        if user_ref.get().exists:
            user_ref.set(user_data, merge=True)
            stats.firestore_users_updated += 1
            stats.actions.append(f"updated firestore user {organization.slug}/{user.id}")
        else:
            user_ref.set(user_data)
            stats.firestore_users_created += 1
            stats.actions.append(f"created firestore user {organization.slug}/{user.id}")

    admin_user = next(user for user in organization.users if user.role == "admin")

    for room in organization.rooms:
        room_ref = org_ref.collection("rooms").document(room.id)
        room_data = {
            "name": room.name,
            "description": room.description,
            "memberIds": user_ids,
            "createdBy": admin_user.id,
            "createdAt": message_created_at(0),
        }

        if dry_run:
            action = "update" if room_ref.get().exists else "create"
            stats.actions.append(f"{action} room {organization.slug}/{room.id}")
            if action == "create":
                stats.rooms_created += 1
            else:
                stats.rooms_updated += 1
        else:
            if room_ref.get().exists:
                room_ref.set(room_data, merge=True)
                stats.rooms_updated += 1
                stats.actions.append(f"updated room {organization.slug}/{room.id}")
            else:
                room_ref.set(room_data)
                stats.rooms_created += 1
                stats.actions.append(f"created room {organization.slug}/{room.id}")

        users_by_id = {user.id: user for user in organization.users}
        for message in room.messages:
            sender = users_by_id[message.sender_id]
            message_ref = room_ref.collection("messages").document(message.id)
            message_data = {
                "senderId": message.sender_id,
                "senderName": sender.name,
                "type": "user",
                "content": message.content,
                "status": "complete",
                "createdAt": message_created_at(message.offset_minutes),
            }

            if dry_run:
                action = "update" if message_ref.get().exists else "create"
                stats.actions.append(f"{action} message {organization.slug}/{room.id}/{message.id}")
                if action == "create":
                    stats.messages_created += 1
                else:
                    stats.messages_updated += 1
                continue

            if message_ref.get().exists:
                message_ref.set(message_data, merge=True)
                stats.messages_updated += 1
            else:
                message_ref.set(message_data)
                stats.messages_created += 1


def seed_all(*, dry_run: bool) -> SeedStats:
    get_firebase_app()
    client = get_firestore_client()
    stats = SeedStats()

    for organization in SEED_ORGANIZATIONS:
        upsert_organization(client, organization, dry_run=dry_run, stats=stats)

    return stats


def print_summary(stats: SeedStats, *, dry_run: bool) -> None:
    prefix = "Dry-run summary" if dry_run else "Seed complete"
    print(f"\n{prefix}:")
    print(f"  organizations: created={stats.organizations_created}, updated={stats.organizations_updated}")
    print(f"  auth users:    created={stats.auth_users_created}, updated={stats.auth_users_updated}")
    print(f"  firestore users: created={stats.firestore_users_created}, updated={stats.firestore_users_updated}")
    print(f"  rooms:         created={stats.rooms_created}, updated={stats.rooms_updated}")
    print(f"  messages:      created={stats.messages_created}, updated={stats.messages_updated}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed TEAMCHAT AI development data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete seeded organizations and auth users before reseeding.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing to Firebase.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.reset:
        print("Resetting seeded organizations and auth users...")
        reset_seed_data(dry_run=args.dry_run)

    stats = seed_all(dry_run=args.dry_run)
    print_summary(stats, dry_run=args.dry_run)

    if not args.dry_run:
        print("\nTest credentials are documented in docs/seed-credentials.md")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
