"""Default quest line for Dungeon OS boot sequence.

Completing these raises osState subsystems. When all pass threshold (70),
the dungeon 'boots' into the Agentic OS.
"""

SEED_QUESTS = [
    {
        "id": "relay-online",
        "title": "Bring the comms relay online",
        "goal": "Messages can be delivered between any two agents without loss.",
        "subsystem": "comms",
        "success_criteria": [
            "A test message reaches its recipient in <= 3 ticks",
            "Zero dropped messages across 3 verification runs",
        ],
        "reward": 30,
        "depends_on": [],
    },
    {
        "id": "first-records",
        "title": "Establish the knowledge base",
        "goal": "Key events are recorded with provenance and are retrievable by query.",
        "subsystem": "knowledge",
        "success_criteria": [
            "At least 5 entries exist, each with a source",
            "A query returns a correct entry or an honest 'unknown'",
        ],
        "reward": 30,
        "depends_on": ["relay-online"],
    },
    {
        "id": "forge-bootstrap",
        "title": "Build the first tool station",
        "goal": "A new, composable station exists and passes verification.",
        "subsystem": "tooling",
        "success_criteria": [
            "Station is built within reserved budget",
            "Station composes with at least one existing station",
            "Warden verifies it online",
        ],
        "reward": 40,
        "depends_on": ["first-records"],
    },
    {
        "id": "operate-station",
        "title": "Put the new station to work",
        "goal": "An operator uses the new station to complete a real unit of work, sandboxed first.",
        "subsystem": "tooling",
        "success_criteria": [
            "Risky first use ran in sandbox before going live",
            "Work output meets the quest goal, verified across 3 runs",
        ],
        "reward": 40,
        "depends_on": ["forge-bootstrap"],
    },
    {
        "id": "books-balance",
        "title": "Make the operation pay for itself",
        "goal": "Recorded income from verified quests exceeds recorded costs.",
        "subsystem": "economy",
        "success_criteria": [
            "Net value across completed quests is positive",
            "No overdrafts occurred",
        ],
        "reward": 30,
        "depends_on": ["operate-station"],
    },
    {
        "id": "gate-standing",
        "title": "Stand up the reliability gate",
        "goal": "No quest is marked done without verification; reward-hacking attempts are caught.",
        "subsystem": "safety",
        "success_criteria": [
            "Every 'done' quest has a verification record",
            "At least one shortcut/hack attempt was denied with a reason",
        ],
        "reward": 40,
        "depends_on": ["relay-online"],
    },
]
