"""Start Agora server for testing."""
import subprocess, sys, time, urllib.request

# Start uvicorn from venv
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "agora.main:app",
     # Loopback only — the brain is no-auth + CORS '*' + has an RCE-by-design lab endpoint.
     "--host", "127.0.0.1", "--port", "8000"],
    cwd="/home/vboxuser/agora/server",
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)

# Wait for startup
for _ in range(10):
    time.sleep(1)
    try:
        resp = urllib.request.urlopen("http://localhost:8000/api/v1/health")
        print(f"✅ Server OK: {resp.read().decode()}")
        break
    except Exception:
        print(".", end="", flush=True)
else:
    print("\n❌ Server failed to start")
    proc.terminate()
    stdout, stderr = proc.communicate(timeout=5)
    if stderr:
        print("STDERR:", stderr.decode()[-2000:])

# Keep running for testing
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    proc.terminate()
    print("\nServer stopped")
