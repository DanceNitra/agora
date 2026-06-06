"""Simple uvicorn runner for Agora."""
import sys
sys.path.insert(0, '.')
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "agora.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
