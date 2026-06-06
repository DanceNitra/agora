"""God API router for Agora server.

Parses and executes divine commands (!spawn, !reward, !punish, !pause,
!resume, !inspect, !inject, !rollback, !reset, !broadcast).
"""

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/god", tags=["god"])


# ---------- Schemas ----------

class CommandRequest(BaseModel):
    command: str  # e.g. "!spawn builder 'Build the great wall'"
    source: Optional[str] = None  # e.g. "telegram:12345"


class CommandResponse(BaseModel):
    parsed_command: str
    args: dict
    result: str
    success: bool


# ---------- Command Parser ----------

def parse_command(raw: str) -> tuple:
    """
    Parse a command string like '!spawn builder "Build the wall"'.

    Returns (command_name, args_dict) where args_dict contains the parsed arguments.
    """
    raw = raw.strip()
    if not raw.startswith("!"):
        raise ValueError("Command must start with '!'")

    parts = _tokenize(raw)
    if not parts:
        raise ValueError("Empty command")

    cmd = parts[0][1:].lower()  # strip '!'
    args = parts[1:]

    parsed_args = {}

    if cmd == "spawn":
        if len(args) < 2:
            raise ValueError("!spawn requires: <role> <instruction> [--name <name>]")
        parsed_args["role"] = args[0]
        # Gather remaining tokens; --name is optional
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

    else:
        raise ValueError(f"Unknown command: !{cmd}")

    return cmd, parsed_args


def _tokenize(text: str) -> list:
    """
    Simple tokenizer that respects quoted strings.
    '!spawn builder "Build the wall"' -> ['!spawn', 'builder', 'Build the wall']
    """
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

async def execute_command(cmd: str, args: dict) -> str:
    """
    Execute a parsed command.  Placeholder — integrates with DB / agent runtime.
    """
    # In production, dispatch to the appropriate subsystem.
    # e.g.:
    #   if cmd == "spawn":
    #       agent = await agent_service.spawn(args["role"], args["instruction"], args.get("name"))
    #       return f"Spawned agent {agent.id}"
    #   if cmd == "reward":
    #       await agent_service.reward(args["agent_id"], args["amount"])
    #       return f"Rewarded agent {args['agent_id']} by {args['amount']}"

    executors = {
        "spawn": lambda a: f"Spawn request: role={a['role']}, instruction={a['instruction']}",
        "reward": lambda a: f"Reward agent {a['agent_id']} by {a['amount']}",
        "punish": lambda a: f"Punish agent {a['agent_id']} by {a['amount']}",
        "pause": lambda a: f"Pause agent {a['agent_id']}",
        "resume": lambda a: f"Resume agent {a['agent_id']}",
        "inspect": lambda a: f"Inspect agent {a['agent_id']}",
        "inject": lambda a: f"Inject message into agent {a['agent_id']}: {a['message']}",
        "rollback": lambda a: f"Rollback agent {a['agent_id']} by {a['steps']} step(s)",
        "reset": lambda a: f"Reset target: {a['target']}",
        "broadcast": lambda a: f"Broadcast: {a['message']}",
    }

    executor = executors.get(cmd)
    if executor is None:
        raise ValueError(f"No executor for command: !{cmd}")

    return executor(args)


# ---------- Dependency ----------

def get_db():
    yield None


# ---------- Routes ----------

@router.post("/command", response_model=CommandResponse)
async def god_command(body: CommandRequest, db=Depends(get_db)):
    """Parse and execute a god-level command."""
    try:
        cmd, args = parse_command(body.command)
        result = await execute_command(cmd, args)
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


