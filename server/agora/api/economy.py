"""Economy API — resource pool, trading, market."""
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/api/v1/economy", tags=["economy"])


def get_economy(request: Request):
    return request.app.state.economy


@router.get("/resources")
async def list_resources(request: Request):
    eco = get_economy(request)
    resources = await eco.get_all_resources()
    result = []
    for r in resources:
        price = await eco.get_market_price(r["id"])
        result.append({**r, "current_price": price})
    return {"resources": result, "total": len(result)}


@router.get("/inventory/{agent_id}")
async def agent_inventory(agent_id: str, request: Request):
    eco = get_economy(request)
    inv = await eco.get_agent_inventory(agent_id)
    return {"agent_id": agent_id, "inventory": inv}


@router.post("/offers")
async def create_offer(
    agent_id: str, offer_type: str, resource_id: int,
    quantity: float, price_per_unit: float, request: Request,
):
    if offer_type not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="offer_type must be 'buy' or 'sell'")
    if quantity <= 0 or price_per_unit <= 0:
        raise HTTPException(status_code=400, detail="quantity and price must be positive")
    eco = get_economy(request)
    result = await eco.create_offer(agent_id, offer_type, resource_id, quantity, price_per_unit)
    return result


@router.get("/offers")
async def list_offers(request: Request, resource_id: int | None = None):
    eco = get_economy(request)
    offers = await eco.get_open_offers(resource_id)
    return {"offers": offers, "total": len(offers)}


@router.get("/history")
async def trade_history(request: Request, limit: int = 20):
    eco = get_economy(request)
    history = await eco.get_trade_history(limit)
    return {"history": history, "total": len(history)}


@router.get("/price/{resource_id}")
async def market_price(resource_id: int, request: Request):
    eco = get_economy(request)
    resource = await eco.get_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    price = await eco.get_market_price(resource_id)
    return {"resource": resource["name"], "current_price": price}


@router.post("/reward")
async def reward_agent(
    agent_id: str, request: Request,
    energy: float = 10.0,
    resource_id: int | None = None,
    quantity: float = 0,
):
    eco = get_economy(request)
    await eco.reward_agent(agent_id, energy, resource_id, quantity)
    return {"status": "rewarded", "agent_id": agent_id, "energy": energy}
