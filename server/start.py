"""Simple uvicorn runner for Agora."""
import sys
sys.path.insert(0, '.')
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "agora.main:app",
        # Loopback only: the brain has no auth, CORS '*', and a /brain/lab/run RCE-by-design
        # endpoint. Binding 0.0.0.0 turns the whole LAN into remote code execution. Keep 127.0.0.1.
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )
