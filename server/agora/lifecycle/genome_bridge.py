"""
GenomeBridge — translates between DB genome format and GenesisForge AgentGenome,
enabling professional mutation on rebirth without rewriting the whole DB layer.
"""
import json
from typing import Any, Optional

from agora.lifecycle.genesis import GenesisForge, AgentGenome


class GenomeBridge:
    """Bidirectional translation + mutation between DB and GenesisForge genomes."""

    # Map DB role → GenesisForge skills
    ROLE_SKILLS = {
        # (researcher/writer/critic removed: skill profiles for the purged old abstract agents.)
        "analyst": ["data_analyse", "web_search", "summarise", "validate"],
        "explorer": ["web_search", "read_file", "code_execute"],
        "adventurer": ["move", "talk", "interact", "explore"],
        "scout": ["move", "web_search", "explore", "talk"],
        "sage": ["talk", "read_file", "summarise", "interact"],
        "blacksmith": ["interact", "use", "move"],
        "alchemist": ["interact", "use", "move", "talk"],
        "merchant": ["talk", "use", "move"],
        "default": ["move", "talk", "wait", "interact"],
    }

    # Map DB personality_traits keys → GenesisForge trait names
    TRAIT_MAP = {
        "curiosity": "curiosity",
        "cooperativeness": "cooperation",
        "thoroughness": "thoroughness",
        "assertiveness": "assertiveness",
    }

    @classmethod
    def db_to_genome(cls, db_genome: dict) -> AgentGenome:
        """Convert a DB-format genome dict to GenesisForge AgentGenome."""
        role = db_genome.get("role", "default")
        skills = cls.ROLE_SKILLS.get(role, cls.ROLE_SKILLS["default"])

        # Map personality traits
        traits = {}
        db_traits = db_genome.get("personality_traits", {})
        for db_key, gf_key in cls.TRAIT_MAP.items():
            val = db_traits.get(db_key, 0.7)
            traits[gf_key] = val

        # Default traits if missing
        for key in ("assertiveness",):
            if key not in traits:
                traits[key] = 0.5

        return AgentGenome(
            skills=list(skills),
            traits=traits,
            max_tool_depth=db_genome.get("max_tool_depth", 3),
            memory_ttl=db_genome.get("memory_ttl", 3600),
            coordination_mode=db_genome.get("coordination_mode", "peer"),
        )

    @classmethod
    def genome_to_db(cls, gf_genome: AgentGenome, db_genome: dict, role: str) -> dict:
        """Convert a GenesisForge AgentGenome back to DB format, preserving extras."""
        # Reverse trait mapping
        personality_traits = {}
        for db_key, gf_key in cls.TRAIT_MAP.items():
            val = gf_genome.traits.get(gf_key, 0.7)
            personality_traits[db_key] = round(val, 4)

        # Map skills → tools (keep DB field name)
        tools = list(gf_genome.skills)

        # Build result — preserve original fields, update mutated ones
        result = dict(db_genome)
        result.update({
            "tools": tools,
            "personality_traits": personality_traits,
            "max_tool_depth": gf_genome.max_tool_depth,
            "memory_ttl": gf_genome.memory_ttl,
            "coordination_mode": gf_genome.coordination_mode,
            "_mutations_applied": 0,  # will be set by caller
            "_last_mutation_gen": db_genome.get("generation", 0),
        })
        return result

    @classmethod
    def mutate_db_genome(cls, db_genome: dict, role: str, generation: int) -> dict:
        """Apply GenesisForge mutation to a DB-format genome and return the result."""
        # Convert to GenesisForge format
        gf_genome = cls.db_to_genome(db_genome)

        # Save pre-mutation state for counting (GenesiseForge mutates in-place)
        old_traits = dict(gf_genome.traits)
        old_skills = set(gf_genome.skills)
        old_depth = gf_genome.max_tool_depth
        old_ttl = gf_genome.memory_ttl
        old_mode = gf_genome.coordination_mode

        # Apply GenesisForge mutation (modifies in-place)
        forge = GenesisForge(seed=hash((json.dumps(db_genome, sort_keys=True), generation)) & 0xFFFFFFFF)
        forge._mutate_genome(gf_genome)

        # Count mutations by comparing pre/post state
        mutations = 0
        for key in gf_genome.traits:
            if abs(old_traits.get(key, 0.5) - gf_genome.traits[key]) > 0.001:
                mutations += 1
        if set(gf_genome.skills) != old_skills:
            mutations += abs(len(gf_genome.skills) - len(old_skills))
        if gf_genome.max_tool_depth != old_depth:
            mutations += 1
        if gf_genome.memory_ttl != old_ttl:
            mutations += 1
        if gf_genome.coordination_mode != old_mode:
            mutations += 1

        # Convert back to DB format
        result = cls.genome_to_db(gf_genome, db_genome, role)
        result["_mutations_applied"] = mutations
        result["_last_mutation_gen"] = generation
        return result

    @classmethod
    def describe_genome(cls, db_genome: dict) -> str:
        """Human-readable summary of a genome."""
        traits = db_genome.get("personality_traits", {})
        tools = db_genome.get("tools", [])
        mode = db_genome.get("coordination_mode", "peer")
        ttl = db_genome.get("memory_ttl", 3600)
        depth = db_genome.get("max_tool_depth", 3)
        mutations = db_genome.get("_mutations_applied", 0)

        trait_str = " | ".join(f"{k}={v:.2f}" for k, v in sorted(traits.items()))
        return (
            f"tools={len(tools)} mode={mode} "
            f"depth={depth} mem_ttl={ttl}s "
            f"traits=[{trait_str}] "
            f"mutations={mutations}"
        )
