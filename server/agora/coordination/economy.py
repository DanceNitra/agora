"""ESS Economy — resource pool, trading, and market dynamics for Agora.

Agents earn energy by completing tasks and can trade resources.
Market prices fluctuate based on supply and demand."""
import json
import math
import random
import sqlite3
import uuid
from datetime import datetime


class EconomyEngine:
    """Economic layer: resource pool, inventory, trading, market pricing."""

    # Default resources seeded on init
    DEFAULT_RESOURCES = [
        {"name": "gold_ore", "base_price": 2.0, "volatility": 0.15},
        {"name": "herbs", "base_price": 1.5, "volatility": 0.2},
        {"name": "crystal_shards", "base_price": 5.0, "volatility": 0.25},
        {"name": "iron_ingot", "base_price": 3.0, "volatility": 0.1},
        {"name": "scroll_fragment", "base_price": 4.0, "volatility": 0.3},
    ]

    # Config (economy_config.py) refers to resources by a 1-based integer id,
    # but the resources table stores UUID ids. This maps config-id N → name
    # (same order as DEFAULT_RESOURCES) so we can resolve to the real UUID.
    RESOURCE_ORDER = ["gold_ore", "herbs", "crystal_shards", "iron_ingot", "scroll_fragment"]

    def __init__(self, db):
        self.db = db
        self._rid_by_name: dict | None = None

    async def _resolve_rid(self, resource_id):
        """Resolve a config integer resource id (1-based) to the real UUID.
        Idempotent: an already-resolved UUID string is returned unchanged."""
        if resource_id is None or isinstance(resource_id, str):
            return resource_id
        try:
            name = self.RESOURCE_ORDER[int(resource_id) - 1]
        except (ValueError, IndexError, TypeError):
            return resource_id
        if self._rid_by_name is None:
            cur = await self.db.execute("SELECT id, name FROM resources")
            self._rid_by_name = {r["name"]: r["id"] for r in await cur.fetchall()}
        return self._rid_by_name.get(name, resource_id)

    async def init_resources(self):
        """Seed default resources if empty."""
        cursor = await self.db.execute("SELECT COUNT(*) as c FROM resources")
        row = await cursor.fetchone()
        if row and row["c"] == 0:
            import uuid
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            for r in self.DEFAULT_RESOURCES:
                rid = str(uuid.uuid4())
                await self.db.execute(
                    "INSERT INTO resources (id, name, total_supply, base_price, volatility, created_at, updated_at) "
                    "VALUES (?, ?, 0, ?, ?, ?, ?)",
                    (rid, r["name"], r["base_price"], r["volatility"], now, now),
                )
            await self.db.commit()
            print(f"[Economy] Seeded {len(self.DEFAULT_RESOURCES)} resources")

    async def get_all_resources(self) -> list[dict]:
        """Get all resources with current market info."""
        cursor = await self.db.execute(
            "SELECT id, name, total_supply, base_price, volatility FROM resources ORDER BY name"
        )
        resources = []
        for row in await cursor.fetchall():
            resources.append(dict(row))
        return resources

    async def get_resource(self, resource_id: int) -> dict | None:
        cursor = await self.db.execute(
            "SELECT id, name, total_supply, base_price, volatility FROM resources WHERE id=?",
            (resource_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_agent_inventory(self, agent_id: str) -> list[dict]:
        """Get inventory for a specific agent."""
        cursor = await self.db.execute(
            """SELECT ai.id, ai.resource_id, ai.quantity, r.name, r.base_price
               FROM agent_inventory ai
               JOIN resources r ON r.id = ai.resource_id
               WHERE ai.agent_id=? AND ai.quantity > 0""",
            (agent_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def add_to_inventory(self, agent_id: str, resource_id: int, quantity: float) -> bool:
        """Add resources to an agent's inventory. Best-effort: a missing FK
        (e.g. a role-config resource_id not present in `resources`) is skipped
        rather than aborting/spamming the economy tick. Returns False if skipped."""
        resource_id = await self._resolve_rid(resource_id)
        try:
            cursor = await self.db.execute(
                "SELECT id, quantity FROM agent_inventory WHERE agent_id=? AND resource_id=?",
                (agent_id, resource_id),
            )
            row = await cursor.fetchone()
            if row:
                await self.db.execute(
                    "UPDATE agent_inventory SET quantity=quantity+? WHERE id=?",
                    (quantity, row["id"]),
                )
            else:
                await self.db.execute(
                    "INSERT INTO agent_inventory (id, agent_id, resource_id, quantity) VALUES (?, ?, ?, ?)",
                    (uuid.uuid4().hex, agent_id, resource_id, quantity),
                )
            # Update total supply
            await self.db.execute(
                "UPDATE resources SET total_supply=total_supply+?, updated_at=datetime('now') WHERE id=?",
                (quantity, resource_id),
            )
            return True
        except sqlite3.IntegrityError:
            return False

    async def remove_from_inventory(self, agent_id: str, resource_id: int, quantity: float) -> bool:
        """Remove resources from inventory. Returns False if insufficient."""
        resource_id = await self._resolve_rid(resource_id)
        cursor = await self.db.execute(
            "SELECT id, quantity FROM agent_inventory WHERE agent_id=? AND resource_id=?",
            (agent_id, resource_id),
        )
        row = await cursor.fetchone()
        if not row or row["quantity"] < quantity:
            return False
        await self.db.execute(
            "UPDATE agent_inventory SET quantity=quantity-? WHERE id=?",
            (quantity, row["id"]),
        )
        await self.db.execute(
            "UPDATE resources SET total_supply=total_supply-?, updated_at=datetime('now') WHERE id=?",
            (quantity, resource_id),
        )
        return True

    async def create_offer(self, agent_id: str, offer_type: str, resource_id: int,
                          quantity: float, price_per_unit: float) -> dict:
        """Create a buy or sell offer."""
        resource_id = await self._resolve_rid(resource_id)
        if offer_type == "sell":
            # Check agent has the resources
            cursor = await self.db.execute(
                "SELECT SUM(quantity) as q FROM agent_inventory WHERE agent_id=? AND resource_id=?",
                (agent_id, resource_id),
            )
            row = await cursor.fetchone()
            if not row or (row["q"] or 0) < quantity:
                return {"status": "error", "message": "Insufficient resources"}

        offer_id = uuid.uuid4().hex
        await self.db.execute(
            "INSERT INTO trade_offers (id, agent_id, offer_type, resource_id, quantity, price_per_unit, status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'open')",
            (offer_id, agent_id, offer_type, resource_id, quantity, price_per_unit),
        )
        await self.db.commit()

        # Try to match immediately
        match = await self._match_offer(offer_id)
        return match or {
            "status": "open",
            "offer_id": offer_id,
            "message": f"Offer #{offer_id[:8]} created (no immediate match)",
        }

    async def _match_offer(self, offer_id: int) -> dict | None:
        """Try to match a new offer with existing opposite offers."""
        cursor = await self.db.execute("SELECT * FROM trade_offers WHERE id=?", (offer_id,))
        offer = await cursor.fetchone()
        if not offer or offer["status"] != "open":
            return None

        opposite = "buy" if offer["offer_type"] == "sell" else "sell"
        price_op = "<=" if offer["offer_type"] == "sell" else ">="

        cursor = await self.db.execute(
            f"""SELECT * FROM trade_offers
                WHERE resource_id=? AND offer_type=? AND status='open' AND id!=?
                AND price_per_unit {price_op} ?
                ORDER BY price_per_unit {'ASC' if offer['offer_type'] == 'sell' else 'DESC'}
                LIMIT 1""",
            (offer["resource_id"], opposite, offer_id, offer["price_per_unit"]),
        )
        match = await cursor.fetchone()
        if not match:
            return None

        # Execute trade at the offer's price (the one that was placed first)
        trade_price = offer["price_per_unit"]
        trade_qty = min(offer["quantity"], match["quantity"])

        total_energy = trade_qty * trade_price

        buyer_id = match["agent_id"] if match["offer_type"] == "buy" else offer["agent_id"]
        seller_id = offer["agent_id"] if offer["offer_type"] == "sell" else match["agent_id"]

        # ── D2: Reputation-based pricing ──
        # Look up mutual trust between buyer and seller
        trust_adjustment = 1.0  # 1.0 = no change
        cursor_trust = await self.db.execute(
            "SELECT score FROM trust_scores "
            "WHERE ((source_id=? AND target_id=?) OR (source_id=? AND target_id=?)) "
            "ORDER BY last_updated DESC LIMIT 1",
            (buyer_id, seller_id, seller_id, buyer_id),
        )
        trust_row = await cursor_trust.fetchone()
        if trust_row:
            trust = trust_row["score"]
            if trust >= 0.7:
                trust_adjustment = 0.9   # 10% discount for trusted partners
            elif trust <= 0.3:
                trust_adjustment = 1.15  # 15% premium for low-trust partners

        trade_price = round(offer["price_per_unit"] * trust_adjustment, 2)
        trade_qty = min(offer["quantity"], match["quantity"])
        cursor = await self.db.execute(
            "SELECT energy_balance FROM agent_identities WHERE agent_id=?",
            (buyer_id,),
        )
        buyer = await cursor.fetchone()
        if not buyer or buyer["energy_balance"] < total_energy:
            return {"status": "error", "message": "Buyer lacks energy"}

        # Check seller has resources
        cursor = await self.db.execute(
            "SELECT SUM(quantity) as q FROM agent_inventory WHERE agent_id=? AND resource_id=?",
            (seller_id, offer["resource_id"]),
        )
        seller_inv = await cursor.fetchone()
        if not seller_inv or (seller_inv["q"] or 0) < trade_qty:
            return {"status": "error", "message": "Seller lacks resources"}

        # Transfer energy
        await self.db.execute(
            "UPDATE agent_identities SET energy_balance=energy_balance-? WHERE agent_id=?",
            (total_energy, buyer_id),
        )
        await self.db.execute(
            "UPDATE agent_identities SET energy_balance=energy_balance+? WHERE agent_id=?",
            (total_energy, seller_id),
        )

        # Transfer resources
        await self.remove_from_inventory(seller_id, offer["resource_id"], trade_qty)
        await self.add_to_inventory(buyer_id, offer["resource_id"], trade_qty)

        # Update offer quantities
        remaining = offer["quantity"] - trade_qty
        if remaining <= 0:
            await self.db.execute(
                "UPDATE trade_offers SET status='filled', filled_at=datetime('now') WHERE id=?",
                (offer_id,),
            )
        else:
            await self.db.execute(
                "UPDATE trade_offers SET quantity=? WHERE id=?", (remaining, offer_id),
            )

        match_remaining = match["quantity"] - trade_qty
        if match_remaining <= 0:
            await self.db.execute(
                "UPDATE trade_offers SET status='filled', filled_at=datetime('now') WHERE id=?",
                (match["id"],),
            )
        else:
            await self.db.execute(
                "UPDATE trade_offers SET quantity=? WHERE id=?", (match_remaining, match["id"]),
            )

        # Record trade history
        await self.db.execute(
            "INSERT INTO trade_history (id, buyer_id, seller_id, resource_id, quantity, price_per_unit, total_energy) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, buyer_id, seller_id, offer["resource_id"], trade_qty, trade_price, total_energy),
        )

        await self.db.commit()

        return {
            "status": "filled",
            "buyer": buyer_id[:8],
            "seller": seller_id[:8],
            "resource_id": offer["resource_id"],
            "quantity": trade_qty,
            "price_per_unit": trade_price,
            "total_energy": total_energy,
        }

    async def get_market_price(self, resource_id: int) -> float:
        """Get current market price based on recent trades and supply."""
        resource_id = await self._resolve_rid(resource_id)
        resource = await self.get_resource(resource_id)
        if not resource:
            return 1.0

        base = resource["base_price"]
        supply = resource["total_supply"]

        # Decrease price with oversupply, increase with scarcity
        if supply > 0:
            supply_factor = max(0.5, min(1.5, 50.0 / (supply + 10)))
        else:
            supply_factor = 1.0

        # Add ongoing trades influence
        cursor = await self.db.execute(
            "SELECT AVG(price_per_unit) as avg_p FROM trade_history WHERE resource_id=?",
            (resource_id,),
        )
        row = await cursor.fetchone()
        avg_trade = row["avg_p"] if row and row["avg_p"] else base

        return round((base * 0.3 + avg_trade * 0.7) * supply_factor, 2)

    async def get_open_offers(self, resource_id: int | None = None) -> list[dict]:
        """Get open trade offers, optionally filtered by resource."""
        resource_id = await self._resolve_rid(resource_id)
        if resource_id:
            cursor = await self.db.execute(
                "SELECT * FROM trade_offers WHERE status='open' AND resource_id=? ORDER BY created_at",
                (resource_id,),
            )
        else:
            cursor = await self.db.execute(
                "SELECT * FROM trade_offers WHERE status='open' ORDER BY created_at"
            )
        return [dict(row) for row in await cursor.fetchall()]

    async def get_trade_history(self, limit: int = 20) -> list[dict]:
        """Get recent trade history."""
        cursor = await self.db.execute(
            "SELECT * FROM trade_history ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def reward_agent(self, agent_id: str, energy: float = 10.0,
                           resource_id: int | None = None, resource_qty: float = 0):
        """Reward an agent with energy and/or resources."""
        await self.db.execute(
            "UPDATE agent_identities SET energy_balance=MIN(energy_balance+?, 100.0) WHERE agent_id=?",
            (energy, agent_id),
        )
        if resource_id and resource_qty > 0:
            await self.add_to_inventory(agent_id, resource_id, resource_qty)
        await self.db.commit()

    async def random_resource_drop(self, agent_id: str, luck: float = 0.3):
        """Randomly drop resources for an agent (e.g. from exploration)."""
        resources = await self.get_all_resources()
        if not resources or random.random() > luck:
            return None
        res = random.choice(resources)
        qty = round(random.uniform(0.5, 3.0), 1)
        await self.add_to_inventory(agent_id, res["id"], qty)
        await self.db.commit()
        return {"resource": res["name"], "quantity": qty}
