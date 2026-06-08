"""Economy configuration — what each role produces and consumes.

Resource IDs (from resources table):
  1 = gold_ore       (base_price: 2.0)
  2 = herbs          (base_price: 1.5)
  3 = crystal_shards (base_price: 5.0)
  4 = iron_ingot     (base_price: 3.0)
  5 = scroll_fragment(base_price: 4.0)

Each role has:
  - produces: (resource_id, qty_per_tick) — what they generate each tick
  - consumes: (resource_id, qty_per_tick) — what they burn each tick
  - needs:    [(resource_id, qty, priority)] — what they try to buy when deficit
"""

# NPC name → economy config
ROLE_ECONOMY = {
    "Shadow Kael": {
        "produces": [(1, 0.5)],              # gold_ore
        "consumes": [(3, 0.2)],              # crystal_shards (for enchantments)
        "surplus_threshold": 3.0,            # sell when inventory > this
        "deficit_threshold": 1.0,            # buy when inventory < this
    },
    "Sage Mira": {
        "produces": [(2, 0.6)],              # herbs
        "consumes": [(5, 0.2)],              # scroll_fragment (maps/knowledge)
        "surplus_threshold": 3.0,
        "deficit_threshold": 1.0,
    },
    "High Priest Orin": {
        "produces": [(5, 0.4)],              # scroll_fragment
        "consumes": [(3, 0.3)],              # crystal_shards (for research)
        "surplus_threshold": 2.0,
        "deficit_threshold": 0.5,
    },
    "King Aldric": {
        "produces": [(4, 0.5)],              # iron_ingot
        "consumes": [(1, 0.3)],              # gold_ore (for smithing)
        "surplus_threshold": 2.0,
        "deficit_threshold": 0.5,
    },
    "Dame Elara": {
        "produces": [(2, 0.4)],              # herbs
        "consumes": [(4, 0.2), (3, 0.1)],   # iron_ingot (tools) + crystal_shards (alchemy)
        "surplus_threshold": 3.0,
        "deficit_threshold": 1.0,
    },
    "Sergeant Voss": {
        "produces": [],                       # guard produces nothing
        "consumes": [(4, 0.1)],              # iron_ingot (weapon maintenance)
        "surplus_threshold": 1.0,
        "deficit_threshold": 0.5,
    },
}


def get_role_config(role: str) -> dict:
    """Get economy config for a role. Returns defaults if role not found."""
    for name, cfg in ROLE_ECONOMY.items():
        if name.lower() == role.lower():
            return cfg
    # Default config for unknown roles
    return {
        "produces": [],
        "consumes": [],
        "surplus_threshold": 3.0,
        "deficit_threshold": 1.0,
    }
