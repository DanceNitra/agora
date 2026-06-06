"""Debug server startup."""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))

async def debug():
    try:
        from agora.main import app, state, init_db, tick_loop
        await init_db()
        print("DB initialized ✅", flush=True)
        
        import uvicorn
        config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
        server = uvicorn.Server(config)
        
        # Start tick loop
        loop = asyncio.get_event_loop()
        loop.create_task(tick_loop())
        print("Tick loop started ✅", flush=True)
        
        await server.serve()
    except Exception as e:
        import traceback
        print(f"ERROR: {e}", flush=True)
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug())
