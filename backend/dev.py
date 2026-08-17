"""Development Server Runner with LAN IP Detection."""

import socket
import uvicorn
from app.config import settings


def get_lan_ip() -> str:
    """Detect LAN IPv4 address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    """Start uvicorn server listening on 0.0.0.0 for LAN access."""
    lan_ip = get_lan_ip()
    port = settings.PORT
    print(f"\n🚀 Starting SideQuest Development Server on LAN...")
    print(f"   🏠 Local:   http://localhost:{port}/docs")
    print(f"   🌐 LAN:     http://{lan_ip}:{port}/docs")
    print(f"   💓 Healthz: http://{lan_ip}:{port}/healthz\n")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    main()
