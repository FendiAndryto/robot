import json
import urllib.request

if __name__ == "__main__":
    payload = {
        "account_number": 12345678,
        "server": "MetaQuotes-Demo",
        "currency": "USD",
        "balance": 10000.0,
        "equity": 10000.0,
        "margin": 0.0,
        "free_margin": 10000.0,
        "margin_level": 0.0,
        "floating_pnl": 0.0,
        "terminal_connected": True,
        "open_positions": 0,
        "timestamp": 1792328000
    }

    req = urllib.request.Request(
        "http://localhost:8089/api/v1/bridge/heartbeat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req) as resp:
        print("Heartbeat Response:", resp.read().decode())

    req_status = urllib.request.Request("http://localhost:8089/api/v1/bridge/status")
    with urllib.request.urlopen(req_status) as resp:
        print("Status Response:", resp.read().decode())

