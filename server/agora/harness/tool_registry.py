"""Tool Registry — Pydantic tool catalog (T v ETCSLV harnesse).

Each NPC ability/skill is registered as a formal ToolDef:
  - Typed parameters (Pydantic models)
  - Execution validation
  - Discovery API: "what can this agent do?"
  - Call validation: "is this tool call valid for this agent?"

Usage:
    registry = ToolRegistry(state_store, db)
    await registry.register_all_abilities()   # load from DB
    tools = await registry.get_tools_for_agent(npc_id)
    result = await registry.call_tool(npc_id, "forge_item", {"material": "iron"})
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Optional, get_type_hints

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════
# DOMAIN MODELS
# ═══════════════════════════════════════════

class AbilityType(str, Enum):
    PASSIVE = "passive"
    ACTIVE = "active"
    ULTIMATE = "ultimate"

class SkillCategory(str, Enum):
    COMBAT = "combat"
    CRAFTING = "crafting"
    KNOWLEDGE = "knowledge"
    EXPLORATION = "exploration"
    SOCIAL = "social"
    SURVIVAL = "survival"
    MAGIC = "magic"


class AgentAbility(BaseModel):
    """An NPC's innate ability — always available (passive) or action-based (active)."""
    name: str = Field(..., description="Unique ability name", max_length=64)
    description: str = Field(..., description="What this ability does", max_length=256)
    power_level: float = Field(default=5.0, ge=0.0, le=10.0, description="Raw power (0–10)")
    ability_type: AbilityType = Field(default=AbilityType.ACTIVE, description="Passive/active/ultimate")
    cooldown_ticks: int = Field(default=0, ge=0, le=100, description="Ticks before reuse")
    energy_cost: float = Field(default=5.0, ge=0.0, le=50.0, description="Energy consumed per use")
    required_skill: Optional[str] = Field(default=None, description="Skill needed to use this ability")


class AgentSkill(BaseModel):
    """A skill the NPC has trained — levelled up via XP."""
    name: str = Field(..., description="Skill name", max_length=64)
    category: SkillCategory = Field(default=SkillCategory.SURVIVAL, description="Skill domain")
    level: int = Field(default=1, ge=0, le=100, description="Current level (0–100)")
    xp: float = Field(default=0.0, ge=0.0, le=9999.0, description="Current XP")
    xp_to_next: float = Field(default=100.0, ge=1.0, le=9999.0, description="XP needed for next level")


class ToolParam(BaseModel):
    """A parameter for a registered tool."""
    name: str = Field(..., max_length=64)
    type_hint: str = Field(default="string", description="Python type hint (string, number, boolean, json)")
    description: str = Field(default="", max_length=256)
    required: bool = Field(default=True)


class ToolDef(BaseModel):
    """A registered tool — typed, validated, discoverable."""
    id: str = Field(..., description="Unique tool identifier (snake_case)")
    name: str = Field(..., description="Human-readable name", max_length=64)
    description: str = Field(..., description="What this tool does", max_length=512)
    parameters: list[ToolParam] = Field(default_factory=list, description="Parameter schema")
    returns: str = Field(default="string", description="Return type hint")
    category: SkillCategory = Field(default=SkillCategory.SURVIVAL, description="Which skill domain")
    min_skill_level: int = Field(default=0, ge=0, le=100, description="Minimum skill level to use")
    energy_cost: float = Field(default=5.0, ge=0.0, le=50.0, description="Energy consumed per call")


class ToolCall(BaseModel):
    """A validated tool invocation."""
    tool_id: str = Field(..., description="Which tool to call")
    agent_id: str = Field(..., description="Who is calling")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ═══════════════════════════════════════════
# BUILT-IN TOOL DEFINITIONS
# ═══════════════════════════════════════════

# Core tools available to all agents
CORE_TOOLS: list[ToolDef] = [
    ToolDef(
        id="move", name="Move", description="Move toward a target position or NPC",
        parameters=[
            ToolParam(name="target_x", type_hint="number", description="Target X coordinate"),
            ToolParam(name="target_y", type_hint="number", description="Target Y coordinate"),
        ],
        category=SkillCategory.EXPLORATION, energy_cost=2.0,
    ),
    ToolDef(
        id="move_to_npc", name="Move To NPC", description="Move toward another NPC",
        parameters=[
            ToolParam(name="npc_name", type_hint="string", description="Name of target NPC"),
        ],
        category=SkillCategory.SOCIAL, energy_cost=2.0,
    ),
    ToolDef(
        id="query_library", name="Query Library", description="Ask the Library Oracle a question",
        parameters=[
            ToolParam(name="question", type_hint="string", description="The question to ask"),
        ],
        category=SkillCategory.KNOWLEDGE, energy_cost=5.0,
    ),
    ToolDef(
        id="create_artifact", name="Create Artifact", description="Create a knowledge artifact",
        parameters=[
            ToolParam(name="title", type_hint="string", description="Artifact title"),
            ToolParam(name="content", type_hint="string", description="Artifact content"),
        ],
        category=SkillCategory.KNOWLEDGE, energy_cost=3.0,
    ),
    ToolDef(
        id="seek_help", name="Seek Help", description="Request help from another NPC",
        parameters=[
            ToolParam(name="helper_name", type_hint="string", description="Who to ask for help"),
            ToolParam(name="problem_type", type_hint="string", description="What kind of help (combat/crafting/knowledge/...)"),
            ToolParam(name="description", type_hint="string", description="What's wrong"),
        ],
        category=SkillCategory.SOCIAL, energy_cost=1.0,
    ),
]

# NPC-specific tools derived from abilities in NPC_DEFS
ABILITY_TO_TOOL_MAP: dict[str, ToolDef] = {
    "Night Vision": ToolDef(
        id="night_vision", name="Night Vision",
        description="See in the dark — increases awareness in dark rooms",
        category=SkillCategory.EXPLORATION, energy_cost=1.0,
    ),
    "Dungeon Sense": ToolDef(
        id="dungeon_sense", name="Dungeon Sense",
        description="Sense danger in underground spaces — detect traps and ambushes",
        category=SkillCategory.EXPLORATION, energy_cost=3.0,
    ),
    "Inspiring Leader": ToolDef(
        id="inspiring_leader", name="Inspiring Leader",
        description="Inspire allies in combat — boost trust and morale",
        category=SkillCategory.SOCIAL, energy_cost=8.0,
    ),
    "Keen Senses": ToolDef(
        id="keen_senses", name="Keen Senses",
        description="Exceptional sight and hearing — detect hidden things",
        category=SkillCategory.EXPLORATION, energy_cost=2.0,
    ),
    "Silent Step": ToolDef(
        id="silent_step", name="Silent Step",
        description="Move without making a sound — avoid detection",
        category=SkillCategory.EXPLORATION, energy_cost=3.0,
    ),
    "Pathfinding": ToolDef(
        id="pathfinding", name="Pathfinding",
        description="Always find the best route — faster navigation",
        category=SkillCategory.EXPLORATION, energy_cost=2.0,
    ),
    "Ancient Lore": ToolDef(
        id="ancient_lore", name="Ancient Lore",
        description="Master ancient languages and history — decipher texts",
        category=SkillCategory.KNOWLEDGE, energy_cost=4.0,
    ),
    "Arcane Sight": ToolDef(
        id="arcane_sight", name="Arcane Sight",
        description="See magical traces — detect enchantments and illusions",
        category=SkillCategory.KNOWLEDGE, energy_cost=4.0,
    ),
    "Dreamwalking": ToolDef(
        id="dreamwalking", name="Dreamwalking",
        description="Communicate through dreams — reach distant allies",
        category=SkillCategory.MAGIC, energy_cost=10.0,
    ),
    "Hammer Mastery": ToolDef(
        id="hammer_mastery", name="Hammer Mastery",
        description="Master the hammer with incredible precision — forge weapons",
        category=SkillCategory.CRAFTING, energy_cost=6.0,
    ),
    "Metal Heart": ToolDef(
        id="metal_heart", name="Metal Heart",
        description="Feel metal and its properties — identify ore quality",
        category=SkillCategory.CRAFTING, energy_cost=3.0,
    ),
    "Forge Fire": ToolDef(
        id="forge_fire", name="Forge Fire",
        description="Maintain ideal forge temperature — perfect smithing conditions",
        category=SkillCategory.CRAFTING, energy_cost=5.0,
    ),
    "Potion Instinct": ToolDef(
        id="potion_instinct", name="Potion Instinct",
        description="Intuitively know which ingredients to combine — perfect potions",
        category=SkillCategory.CRAFTING, energy_cost=5.0,
    ),
    "Toxic Resistance": ToolDef(
        id="toxic_resistance", name="Toxic Resistance",
        description="Resistant to poisons and toxins — handle dangerous ingredients",
        category=SkillCategory.SURVIVAL, energy_cost=1.0,
    ),
    "Brewing Genius": ToolDef(
        id="brewing_genius", name="Brewing Genius",
        description="Create unique elixirs with special properties",
        category=SkillCategory.CRAFTING, energy_cost=8.0,
    ),
    "Silver Tongue": ToolDef(
        id="silver_tongue", name="Silver Tongue",
        description="Persuade anyone — negotiate, barter, deceive",
        category=SkillCategory.SOCIAL, energy_cost=4.0,
    ),
    "Trade Instinct": ToolDef(
        id="trade_instinct", name="Trade Instinct",
        description="Sense advantageous trades — know a good deal when you see it",
        category=SkillCategory.SOCIAL, energy_cost=2.0,
    ),
    "Networker": ToolDef(
        id="networker", name="Networker",
        description="Know people and their needs — leverage connections",
        category=SkillCategory.SOCIAL, energy_cost=3.0,
    ),
    "Iron Will": ToolDef(
        id="iron_will", name="Iron Will",
        description="Unshakeable discipline — resist fear and manipulation",
        category=SkillCategory.SURVIVAL, energy_cost=2.0,
    ),
    "Sentinel": ToolDef(
        id="sentinel", name="Sentinel",
        description="Never sleeps on guard — detect intruders even while resting",
        category=SkillCategory.SURVIVAL, energy_cost=1.0,
    ),
    "Shield Wall": ToolDef(
        id="shield_wall", name="Shield Wall",
        description="Protect allies with a shield — group defense",
        category=SkillCategory.COMBAT, energy_cost=6.0,
    ),
}


class ToolRegistry:
    """Pydantic tool catalog — register, discover, validate, and call agent tools."""

    def __init__(self, state_store, db):
        self.state_store = state_store
        self.db = db
        # id -> ToolDef
        self._tools: dict[str, ToolDef] = {}
        # npc_id -> list[ToolDef] (runtime cache)
        self._agent_tools: dict[str, list[ToolDef]] = {}
        # Register core tools on init
        self._register_core_tools()

    def _register_core_tools(self):
        """Register universal tools available to every agent."""
        for tool in CORE_TOOLS:
            self._tools[tool.id] = tool

        # Register skill-derived tools globally too
        skill_tools = [
            ToolDef(id="attack_melee", name="Melee Attack",
                description="Attack a target with your melee weapon",
                parameters=[ToolParam(name="target", type_hint="string", description="Target NPC name")],
                category=SkillCategory.COMBAT, energy_cost=5.0, min_skill_level=0),
            ToolDef(id="scout_area", name="Scout Area",
                description="Explore the current room for secrets",
                category=SkillCategory.EXPLORATION, energy_cost=3.0),
            ToolDef(id="climb", name="Climb",
                description="Climb walls or obstacles",
                parameters=[ToolParam(name="target_height", type_hint="number", description="Height to climb")],
                category=SkillCategory.EXPLORATION, energy_cost=5.0),
            ToolDef(id="hide", name="Hide",
                description="Hide from enemies or observers",
                category=SkillCategory.EXPLORATION, energy_cost=3.0),
            ToolDef(id="track", name="Track",
                description="Follow tracks of a creature or NPC",
                parameters=[ToolParam(name="target", type_hint="string", description="Who to track")],
                category=SkillCategory.EXPLORATION, energy_cost=2.0),
            ToolDef(id="cast_ritual", name="Cast Ritual",
                description="Perform an arcane ritual using knowledge of magic",
                category=SkillCategory.MAGIC, energy_cost=10.0),
            ToolDef(id="brew_potion", name="Brew Potion",
                description="Brew a potion from ingredients",
                category=SkillCategory.CRAFTING, energy_cost=5.0),
            ToolDef(id="forge_item", name="Forge Item",
                description="Forge a metal item at the forge",
                parameters=[ToolParam(name="item_type", type_hint="string", description="What to forge")],
                category=SkillCategory.CRAFTING, energy_cost=6.0),
            ToolDef(id="negotiate", name="Negotiate",
                description="Negotiate a deal with another NPC",
                parameters=[ToolParam(name="partner", type_hint="string"), ToolParam(name="deal", type_hint="string")],
                category=SkillCategory.SOCIAL, energy_cost=3.0),
            ToolDef(id="heal", name="Heal",
                description="Heal an NPC (self or other)",
                parameters=[ToolParam(name="target", type_hint="string"), ToolParam(name="amount", type_hint="number")],
                category=SkillCategory.SURVIVAL, energy_cost=5.0),
        ]
        for tool in skill_tools:
            self._tools[tool.id] = tool

        # Register all ability-to-tool mappings globally too
        for ability_name, ability_tool in ABILITY_TO_TOOL_MAP.items():
            if ability_tool.id not in self._tools:
                self._tools[ability_tool.id] = ability_tool

    # ═══════════════════════════════════════════
    # REGISTRATION
    # ═══════════════════════════════════════════

    def register_tool(self, tool: ToolDef):
        """Register or update a tool definition."""
        self._tools[tool.id] = tool
        print(f"[ToolRegistry] Registered tool: {tool.id} ({tool.name})")

    def register_ability_tool(self, ability_name: str) -> Optional[ToolDef]:
        """Register tool from the ability->tool map. Returns the tool or None."""
        tool = ABILITY_TO_TOOL_MAP.get(ability_name)
        if tool:
            self._tools[tool.id] = tool
            return tool
        return None

    # ═══════════════════════════════════════════
    # DISCOVERY
    # ═══════════════════════════════════════════

    async def get_tools_for_agent(self, agent_id: str) -> list[ToolDef]:
        """Discover all tools available to an agent — core + abilities + skills."""
        if agent_id in self._agent_tools:
            return self._agent_tools[agent_id]

        tools = list(CORE_TOOLS)  # start with core

        # Add ability-based tools
        if self.state_store:
            try:
                cursor = await self.db.execute(
                    "SELECT ability_name, power_level, is_passive FROM agent_abilities WHERE npc_id=?",
                    (agent_id,),
                )
                abilities = await cursor.fetchall()

                for ab in abilities:
                    ability_tool = ABILITY_TO_TOOL_MAP.get(ab["ability_name"])
                    if ability_tool:
                        # Create a copy with NPC-specific energy cost scaling
                        power = ab["power_level"]
                        cost_scale = max(0.5, 2.0 - power / 10.0)  # higher power = lower cost
                        scaled_tool = ability_tool.model_copy(update={
                            "energy_cost": round(ability_tool.energy_cost * cost_scale, 1),
                            "min_skill_level": max(0, int(10 - power)),  # higher power = lower skill req
                        })
                        tools.append(scaled_tool)

                # Add skill-based tools (skills enable actions)
                skill_cursor = await self.db.execute(
                    "SELECT skill_name, level, xp FROM agent_skills WHERE npc_id=?",
                    (agent_id,),
                )
                skills = await skill_cursor.fetchall()
                for sk in skills:
                    skill_tool = self._skill_to_tool(sk["skill_name"], sk["level"])
                    if skill_tool:
                        tools.append(skill_tool)

            except Exception as e:
                print(f"[ToolRegistry] Discovery error for {agent_id[:8]}: {e}")

        self._agent_tools[agent_id] = tools
        return tools

    def _skill_to_tool(self, skill_name: str, level: int) -> Optional[ToolDef]:
        """Derive a ToolDef from a skill (skills unlock higher-level actions)."""
        skill_tool_map = {
            "swordfighting": ToolDef(
                id="attack_melee", name="Melee Attack",
                description="Attack a target with your melee weapon",
                parameters=[ToolParam(name="target", type_hint="string", description="Target NPC name")],
                category=SkillCategory.COMBAT, energy_cost=max(2.0, 10.0 - level * 0.8),
            ),
            "exploration": ToolDef(
                id="scout_area", name="Scout Area", description="Explore the current room for secrets",
                category=SkillCategory.EXPLORATION, energy_cost=max(1.0, 5.0 - level * 0.5),
            ),
            "climbing": ToolDef(
                id="climb", name="Climb", description="Climb walls or obstacles",
                parameters=[ToolParam(name="target_height", type_hint="number", description="Height to climb")],
                category=SkillCategory.EXPLORATION, energy_cost=max(2.0, 8.0 - level * 0.6),
            ),
            "stealth": ToolDef(
                id="hide", name="Hide", description="Hide from enemies or observers",
                category=SkillCategory.EXPLORATION, energy_cost=3.0,
            ),
            "tracking": ToolDef(
                id="track", name="Track", description="Follow tracks of a creature or NPC",
                parameters=[ToolParam(name="target", type_hint="string", description="Who to track")],
                category=SkillCategory.EXPLORATION, energy_cost=2.0,
            ),
            "arcana": ToolDef(
                id="cast_ritual", name="Cast Ritual",
                description="Perform an arcane ritual using knowledge of magic",
                category=SkillCategory.MAGIC, energy_cost=max(3.0, 12.0 - level),
            ),
            "alchemy": ToolDef(
                id="brew_potion", name="Brew Potion",
                description="Brew a potion from ingredients",
                category=SkillCategory.CRAFTING, energy_cost=5.0,
            ),
            "smithing": ToolDef(
                id="forge_item", name="Forge Item",
                description="Forge a metal item at the forge",
                parameters=[ToolParam(name="item_type", type_hint="string", description="What to forge")],
                category=SkillCategory.CRAFTING, energy_cost=6.0,
            ),
            "bargaining": ToolDef(
                id="negotiate", name="Negotiate", description="Negotiate a deal with another NPC",
                parameters=[ToolParam(name="partner", type_hint="string"), ToolParam(name="deal", type_hint="string")],
                category=SkillCategory.SOCIAL, energy_cost=3.0,
            ),
            "healing": ToolDef(
                id="heal", name="Heal", description="Heal an NPC (self or other)",
                parameters=[ToolParam(name="target", type_hint="string"), ToolParam(name="amount", type_hint="number")],
                category=SkillCategory.SURVIVAL, energy_cost=5.0,
            ),
        }
        return skill_tool_map.get(skill_name)

    async def invalidate_agent_cache(self, agent_id: str):
        """Clear the cached tool list for an agent (call after new ability/skill learned)."""
        self._agent_tools.pop(agent_id, None)

    # ═══════════════════════════════════════════
    # VALIDATION
    # ═══════════════════════════════════════════

    def get_tool(self, tool_id: str) -> Optional[ToolDef]:
        """Look up a tool definition by ID."""
        return self._tools.get(tool_id)

    def validate_call(self, tool_call: ToolCall) -> Optional[str]:
        """Validate a tool call against the registered ToolDef. Returns error or None."""
        tool = self._tools.get(tool_call.tool_id)
        if not tool:
            return f"Unknown tool: {tool_call.tool_id}"

        # Validate parameters
        for param in tool.parameters:
            if param.required and param.name not in tool_call.parameters:
                return f"Missing required parameter '{param.name}' for tool '{tool.id}'"

            value = tool_call.parameters.get(param.name)
            if value is not None:
                # Type validation
                if param.type_hint == "number":
                    if not isinstance(value, (int, float)):
                        return f"Parameter '{param.name}' should be number, got {type(value).__name__}"
                elif param.type_hint == "string":
                    if not isinstance(value, str):
                        return f"Parameter '{param.name}' should be string, got {type(value).__name__}"
                elif param.type_hint == "boolean":
                    if not isinstance(value, bool):
                        return f"Parameter '{param.name}' should be boolean, got {type(value).__name__}"

        return None  # valid

    async def can_agent_use_tool(self, agent_id: str, tool_id: str) -> tuple[bool, str]:
        """Check if an agent has access to a tool and meets requirements."""
        tool = self._tools.get(tool_id)
        if not tool:
            return False, f"Tool '{tool_id}' not found"

        # Check energy cost
        if self.state_store:
            agent = await self.state_store.get_agent(agent_id)
            if agent and agent.get("energy_balance", 0) < tool.energy_cost:
                return False, f"Agent needs {tool.energy_cost} energy, has {agent['energy_balance']:.0f}"

        # Check skill requirements
        if tool.min_skill_level > 0 and self.state_store:
            skills = await self.state_store.get_all_skills(agent_id)
            has_skill = any(s["level"] >= tool.min_skill_level for s in skills)
            if not has_skill:
                return False, f"Agent needs skill level {tool.min_skill_level}+ to use '{tool.name}'"

        return True, "ok"

    # ═══════════════════════════════════════════
    # EXECUTION
    # ═══════════════════════════════════════════

    async def call_tool(
        self,
        agent_id: str,
        tool_id: str,
        params: dict[str, Any],
        broadcast_fn=None,
    ) -> dict:
        """Execute a tool call with full validation. Returns result dict."""
        tool_call = ToolCall(tool_id=tool_id, agent_id=agent_id, parameters=params)

        # Validate structure
        error = self.validate_call(tool_call)
        if error:
            return {"status": "error", "error": error}

        # Check agent permissions
        can_use, msg = await self.can_agent_use_tool(agent_id, tool_id)
        if not can_use:
            return {"status": "error", "error": msg}

        # Deduct energy
        tool_def = self._tools[tool_id]
        if self.state_store:
            await self.state_store.update_agent(agent_id, {
                "energy_balance": -tool_def.energy_cost,  # negative = deduction
            })

        result = {
            "status": "success",
            "tool_id": tool_id,
            "agent_id": agent_id[:8],
            "params": params,
            "energy_cost": tool_def.energy_cost,
        }

        if broadcast_fn:
            await broadcast_fn("tool_call", {
                "agent_id": agent_id[:8],
                "tool": tool_id,
                "params": params,
                "energy_cost": tool_def.energy_cost,
            })

        return result

    # ═══════════════════════════════════════════
    # QUERIES
    # ═══════════════════════════════════════════

    def list_all_tools(self) -> list[ToolDef]:
        """List all registered tools."""
        return list(self._tools.values())

    def list_tools_by_category(self, category: SkillCategory) -> list[ToolDef]:
        """Filter tools by skill category."""
        return [t for t in self._tools.values() if t.category == category]
