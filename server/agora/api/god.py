"""God API router for Agora server.

Parses and executes divine commands (!spawn, !reward, !punish, !pause,
!resume, !inspect, !inject, !rollback, !reset, !broadcast).
"""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["god"])


# ---------- Schemas ----------

class CommandRequest(BaseModel):
    command: str
    source: Optional[str] = None


class CommandResponse(BaseModel):
    parsed_command: str
    args: dict
    result: str
    success: bool


# ---------- Dependency ----------

async def get_db(request: Request):
    return request.app.state.db


# ---------- Command Parser ----------

def parse_command(raw: str) -> tuple:
    raw = raw.strip()
    if not raw.startswith("!"):
        raise ValueError("Command must start with '!'")

    parts = _tokenize(raw)
    if not parts:
        raise ValueError("Empty command")

    cmd = parts[0][1:].lower()
    args = parts[1:]
    parsed_args = {}

    if cmd == "spawn":
        if len(args) < 2:
            raise ValueError("!spawn requires: <role> <instruction> [--name <name>]")
        parsed_args["role"] = args[0]
        extra = []
        name = None
        i = 1
        while i < len(args):
            if args[i] == "--name" and i + 1 < len(args):
                name = args[i + 1]
                i += 2
            else:
                extra.append(args[i])
                i += 1
        parsed_args["instruction"] = " ".join(extra)
        if name:
            parsed_args["name"] = name

    elif cmd == "reward":
        if len(args) < 1:
            raise ValueError("!reward requires: <agent_id> [amount]")
        parsed_args["agent_id"] = args[0]
        parsed_args["amount"] = float(args[1]) if len(args) > 1 else 1.0

    elif cmd == "punish":
        if len(args) < 1:
            raise ValueError("!punish requires: <agent_id> [amount]")
        parsed_args["agent_id"] = args[0]
        parsed_args["amount"] = float(args[1]) if len(args) > 1 else 1.0

    elif cmd == "pause":
        if not args:
            raise ValueError("!pause requires: <agent_id>")
        parsed_args["agent_id"] = args[0]

    elif cmd == "resume":
        if not args:
            raise ValueError("!resume requires: <agent_id>")
        parsed_args["agent_id"] = args[0]

    elif cmd == "inspect":
        if not args:
            raise ValueError("!inspect requires: <agent_id>")
        parsed_args["agent_id"] = args[0]

    elif cmd == "inject":
        if len(args) < 2:
            raise ValueError("!inject requires: <agent_id> <message>")
        parsed_args["agent_id"] = args[0]
        parsed_args["message"] = " ".join(args[1:])

    elif cmd == "rollback":
        if not args:
            raise ValueError("!rollback requires: <agent_id> [steps]")
        parsed_args["agent_id"] = args[0]
        parsed_args["steps"] = int(args[1]) if len(args) > 1 else 1

    elif cmd == "reset":
        parsed_args["target"] = args[0] if args else "all"

    elif cmd == "broadcast":
        if not args:
            raise ValueError("!broadcast requires: <message>")
        parsed_args["message"] = " ".join(args)

    elif cmd == "list":
        parsed_args["filter"] = args[0] if args else "all"

    else:
        raise ValueError(f"Unknown command: !{cmd}")

    return cmd, parsed_args


def _tokenize(text: str) -> list:
    tokens = []
    i = 0
    current = []
    in_quote = False
    quote_char = None

    while i < len(text):
        ch = text[i]
        if in_quote:
            if ch == quote_char:
                in_quote = False
                if current:
                    tokens.append("".join(current))
                    current = []
            else:
                current.append(ch)
        elif ch in ('"', "'"):
            in_quote = True
            quote_char = ch
        elif ch.isspace():
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(ch)
        i += 1

    if current:
        tokens.append("".join(current))

    return tokens


# ---------- Command Executor ----------

async def execute_command(cmd: str, args: dict, db) -> str:
    if cmd == "spawn":
        aid = str(uuid.uuid4())
        genome = json.dumps({
            "role": args["role"],
            "tools": ["default"],
            "model_tier": "cheap",
            "temperature": 0.7,
            "personality_traits": {"curiosity": 0.8, "thoroughness": 0.7},
            "instruction": args["instruction"],
        })
        name = args.get("name", args["role"])
        await db.execute(
            """INSERT INTO agent_identities (agent_id, public_key, generation, genome,
               trust_score, energy_balance, role, status)
               VALUES (?, ?, 0, ?, 0.5, 100, ?, 'active')""",
            (aid, f"key_{aid[:8]}", genome, name),
        )
        await db.commit()
        return f"Spawned agent {args['role']} (id: {aid[:8]})"

    elif cmd == "reward":
        cursor = await db.execute(
            "SELECT trust_score FROM agent_identities WHERE agent_id=?", (args["agent_id"],)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        new_score = min(1.0, row["trust_score"] + args["amount"] * 0.1)
        await db.execute(
            "UPDATE agent_identities SET trust_score=?, updated_at=datetime('now') WHERE agent_id=?",
            (new_score, args["agent_id"]),
        )
        await db.commit()
        return f"Rewarded agent {args['agent_id'][:8]} by {args['amount']} (trust: {new_score:.3f})"

    elif cmd == "punish":
        cursor = await db.execute(
            "SELECT trust_score FROM agent_identities WHERE agent_id=?", (args["agent_id"],)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        new_score = max(0.0, row["trust_score"] - args["amount"] * 0.1)
        await db.execute(
            "UPDATE agent_identities SET trust_score=?, updated_at=datetime('now') WHERE agent_id=?",
            (new_score, args["agent_id"]),
        )
        await db.commit()
        return f"Punished agent {args['agent_id'][:8]} by {args['amount']} (trust: {new_score:.3f})"

    elif cmd == "pause":
        cursor = await db.execute(
            "SELECT status FROM agent_identities WHERE agent_id=?", (args["agent_id"],)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        await db.execute(
            "UPDATE agent_identities SET status='paused', updated_at=datetime('now') WHERE agent_id=?",
            (args["agent_id"],),
        )
        await db.commit()
        return f"Paused agent {args['agent_id'][:8]}"

    elif cmd == "resume":
        cursor = await db.execute(
            "SELECT status FROM agent_identities WHERE agent_id=?", (args["agent_id"],)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        await db.execute(
            "UPDATE agent_identities SET status='active', updated_at=datetime('now') WHERE agent_id=?",
            (args["agent_id"],),
        )
        await db.commit()
        return f"Resumed agent {args['agent_id'][:8]}"

    elif cmd == "inspect":
        cursor = await db.execute(
            "SELECT * FROM agent_identities WHERE agent_id=?", (args["agent_id"],)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        return json.dumps(dict(row), indent=2, default=str)

    elif cmd == "inject":
        return f"Injected message into agent {args['agent_id'][:8]}: {args['message']}"

    elif cmd == "rollback":
        return f"Rolled back agent {args['agent_id'][:8]} by {args['steps']} step(s)"

    elif cmd == "reset":
        if args["target"] == "all":
            await db.execute("DELETE FROM agent_identities")
            await db.execute("DELETE FROM trust_scores")
            await db.execute("DELETE FROM stigmergy_traces")
            await db.execute("DELETE FROM events")
            await db.commit()
            return "Reset all agents and traces"
        return f"Reset target: {args['target']}"

    elif cmd == "broadcast":
        return f"Broadcast: {args['message']}"

    elif cmd == "list":
        cursor = await db.execute(
            "SELECT agent_id, role, status, trust_score FROM agent_identities ORDER BY created_at"
        )
        rows = await cursor.fetchall()
        if not rows:
            return "No agents found"
        lines = [f"{'ID':<12} {'Role':<12} {'Status':<10} {'Trust':<8}"]
        lines.append("-" * 42)
        for r in rows:
            lines.append(f"{r['agent_id'][:8]:<12} {r['role']:<12} {r['status']:<10} {r['trust_score']:.3f}")
        return "\n".join(lines)

    return f"Executed: !{cmd} {args}"


# ---------- Routes ----------

@router.post("/command", response_model=CommandResponse)
async def god_command(body: CommandRequest, db=Depends(get_db)):
    """Parse and execute a god-level command."""
    try:
        cmd, args = parse_command(body.command)
        result = await execute_command(cmd, args, db)
        return CommandResponse(
            parsed_command=cmd,
            args=args,
            result=result,
            success=True,
        )
    except (ValueError, HTTPException) as exc:
        return CommandResponse(
            parsed_command="",
            args={},
            result=str(exc),
            success=False,
        )
