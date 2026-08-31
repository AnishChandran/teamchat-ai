"""Static seed definitions for local development."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


DEFAULT_SEED_PASSWORD = "TeamChatDev123!"

SEED_BASE_TIME = datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class SeedUser:
    id: str
    name: str
    email: str
    role: str


@dataclass(frozen=True)
class SeedMessage:
    id: str
    sender_id: str
    content: str
    offset_minutes: int


@dataclass(frozen=True)
class SeedRoom:
    id: str
    name: str
    description: str
    messages: list[SeedMessage] = field(default_factory=list)


@dataclass(frozen=True)
class SeedOrganization:
    id: str
    name: str
    slug: str
    users: list[SeedUser]
    rooms: list[SeedRoom]


ACME_ORG = SeedOrganization(
    id="acme",
    name="Acme Inc",
    slug="acme",
    users=[
        SeedUser(id="sarah", name="Sarah", email="sarah@acme.test", role="admin"),
        SeedUser(id="mike", name="Mike", email="mike@acme.test", role="member"),
        SeedUser(id="lisa", name="Lisa", email="lisa@acme.test", role="member"),
    ],
    rooms=[
        SeedRoom(
            id="general",
            name="General",
            description="Company-wide announcements and casual chat",
            messages=[
                SeedMessage(
                    id="general-001",
                    sender_id="sarah",
                    content="Good morning everyone! Welcome to the new Acme team chat.",
                    offset_minutes=0,
                ),
                SeedMessage(
                    id="general-002",
                    sender_id="mike",
                    content="Morning Sarah! Excited to have everything in one place.",
                    offset_minutes=8,
                ),
                SeedMessage(
                    id="general-003",
                    sender_id="lisa",
                    content="Same here. I'll share the onboarding deck here later today.",
                    offset_minutes=15,
                ),
                SeedMessage(
                    id="general-004",
                    sender_id="sarah",
                    content="Reminder: all-hands is Thursday at 2pm. Please block your calendars.",
                    offset_minutes=45,
                ),
                SeedMessage(
                    id="general-005",
                    sender_id="mike",
                    content="Got it. Will the Q1 roadmap review happen in that meeting?",
                    offset_minutes=52,
                ),
                SeedMessage(
                    id="general-006",
                    sender_id="sarah",
                    content="Yes — we'll cover roadmap, hiring, and the launch timeline.",
                    offset_minutes=58,
                ),
                SeedMessage(
                    id="general-007",
                    sender_id="lisa",
                    content="I'll prep the customer feedback summary before then.",
                    offset_minutes=70,
                ),
                SeedMessage(
                    id="general-008",
                    sender_id="mike",
                    content="Thanks Lisa. I'll add the latest usage metrics to the deck.",
                    offset_minutes=85,
                ),
                SeedMessage(
                    id="general-009",
                    sender_id="sarah",
                    content="Perfect. Let's keep async updates in this room this week.",
                    offset_minutes=110,
                ),
                SeedMessage(
                    id="general-010",
                    sender_id="lisa",
                    content="Sounds good. I'll post the draft agenda tomorrow morning.",
                    offset_minutes=125,
                ),
            ],
        ),
        SeedRoom(
            id="engineering",
            name="Engineering",
            description="Technical discussions, code reviews, and sprint coordination",
            messages=[
                SeedMessage(
                    id="engineering-001",
                    sender_id="mike",
                    content="Sprint planning notes are in the wiki. Please review before standup.",
                    offset_minutes=0,
                ),
                SeedMessage(
                    id="engineering-002",
                    sender_id="lisa",
                    content="I finished the auth middleware refactor. PR is ready for review.",
                    offset_minutes=20,
                ),
                SeedMessage(
                    id="engineering-003",
                    sender_id="sarah",
                    content="Nice work Lisa. I'll take a look after lunch.",
                    offset_minutes=28,
                ),
                SeedMessage(
                    id="engineering-004",
                    sender_id="mike",
                    content="We need to add indexes for the room message queries before launch.",
                    offset_minutes=40,
                ),
                SeedMessage(
                    id="engineering-005",
                    sender_id="lisa",
                    content="Already on it — I'll open a ticket for the composite index.",
                    offset_minutes=47,
                ),
                SeedMessage(
                    id="engineering-006",
                    sender_id="mike",
                    content="Standup summary: auth done, messaging in progress, deployment next.",
                    offset_minutes=90,
                ),
                SeedMessage(
                    id="engineering-007",
                    sender_id="sarah",
                    content="Let's target staging deploy on Wednesday if tests stay green.",
                    offset_minutes=105,
                ),
                SeedMessage(
                    id="engineering-008",
                    sender_id="lisa",
                    content="WebSocket load test passed with 200 concurrent connections.",
                    offset_minutes=130,
                ),
                SeedMessage(
                    id="engineering-009",
                    sender_id="mike",
                    content="Great numbers. I'll bump the Cloud Run min instances for the demo.",
                    offset_minutes=145,
                ),
                SeedMessage(
                    id="engineering-010",
                    sender_id="sarah",
                    content="Thanks team. Flag any blockers here before EOD.",
                    offset_minutes=160,
                ),
            ],
        ),
    ],
)

GLOBEX_ORG = SeedOrganization(
    id="globex",
    name="Globex Corp",
    slug="globex",
    users=[
        SeedUser(id="john", name="John", email="john@globex.test", role="admin"),
        SeedUser(id="jane", name="Jane", email="jane@globex.test", role="member"),
        SeedUser(id="bob", name="Bob", email="bob@globex.test", role="member"),
    ],
    rooms=[
        SeedRoom(
            id="general",
            name="General",
            description="Company-wide announcements and casual chat",
            messages=[
                SeedMessage(
                    id="general-001",
                    sender_id="john",
                    content="Welcome to Globex team chat! Use this room for company updates.",
                    offset_minutes=0,
                ),
                SeedMessage(
                    id="general-002",
                    sender_id="jane",
                    content="Thanks John. Happy to have a dedicated space for the team.",
                    offset_minutes=12,
                ),
                SeedMessage(
                    id="general-003",
                    sender_id="bob",
                    content="I'll share the customer onboarding checklist here this afternoon.",
                    offset_minutes=25,
                ),
                SeedMessage(
                    id="general-004",
                    sender_id="john",
                    content="Reminder: benefits enrollment closes Friday.",
                    offset_minutes=50,
                ),
                SeedMessage(
                    id="general-005",
                    sender_id="jane",
                    content="Does that include the updated dental plan options?",
                    offset_minutes=58,
                ),
                SeedMessage(
                    id="general-006",
                    sender_id="john",
                    content="Yes — HR posted the comparison sheet in the shared drive.",
                    offset_minutes=65,
                ),
                SeedMessage(
                    id="general-007",
                    sender_id="bob",
                    content="I'll nudge the sales team to add their pipeline notes before the review.",
                    offset_minutes=95,
                ),
                SeedMessage(
                    id="general-008",
                    sender_id="jane",
                    content="Product launch dry run is scheduled for next Tuesday.",
                    offset_minutes=120,
                ),
                SeedMessage(
                    id="general-009",
                    sender_id="john",
                    content="Please keep launch-related updates in this room this week.",
                    offset_minutes=135,
                ),
                SeedMessage(
                    id="general-010",
                    sender_id="bob",
                    content="Will do. I'll post the revised timeline once finance signs off.",
                    offset_minutes=150,
                ),
            ],
        ),
        SeedRoom(
            id="engineering",
            name="Engineering",
            description="Technical discussions, code reviews, and sprint coordination",
            messages=[
                SeedMessage(
                    id="engineering-001",
                    sender_id="jane",
                    content="API contract for the billing service is finalized. Link in the ticket.",
                    offset_minutes=0,
                ),
                SeedMessage(
                    id="engineering-002",
                    sender_id="bob",
                    content="I can start the integration tests once the staging env is refreshed.",
                    offset_minutes=18,
                ),
                SeedMessage(
                    id="engineering-003",
                    sender_id="john",
                    content="Staging refresh is queued for tonight. I'll ping you when it's done.",
                    offset_minutes=30,
                ),
                SeedMessage(
                    id="engineering-004",
                    sender_id="jane",
                    content="We should add retry logic to the webhook consumer before go-live.",
                    offset_minutes=55,
                ),
                SeedMessage(
                    id="engineering-005",
                    sender_id="bob",
                    content="Agreed. I have a draft PR for exponential backoff.",
                    offset_minutes=63,
                ),
                SeedMessage(
                    id="engineering-006",
                    sender_id="john",
                    content="Standup: billing integration on track, observability dashboard next.",
                    offset_minutes=100,
                ),
                SeedMessage(
                    id="engineering-007",
                    sender_id="jane",
                    content="Latency on the search endpoint is down 18% after the cache change.",
                    offset_minutes=115,
                ),
                SeedMessage(
                    id="engineering-008",
                    sender_id="bob",
                    content="Nice! I'll roll the same pattern to the recommendations service.",
                    offset_minutes=128,
                ),
                SeedMessage(
                    id="engineering-009",
                    sender_id="john",
                    content="Let's keep the release branch frozen until QA signs off.",
                    offset_minutes=150,
                ),
                SeedMessage(
                    id="engineering-010",
                    sender_id="jane",
                    content="QA reported two minor UI issues — fixes should land by tomorrow.",
                    offset_minutes=165,
                ),
            ],
        ),
    ],
)

SEED_ORGANIZATIONS: list[SeedOrganization] = [ACME_ORG, GLOBEX_ORG]


def message_created_at(offset_minutes: int) -> datetime:
    return SEED_BASE_TIME + timedelta(minutes=offset_minutes)


def all_seed_emails() -> list[str]:
    return [user.email for org in SEED_ORGANIZATIONS for user in org.users]
