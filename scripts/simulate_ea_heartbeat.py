import time
import json
import urllib.request
import random

def run_simulation(duration_seconds=300):
    url = "http://127.0.0.1:8089/api/v1/bridge/heartbeat"
    balance = 25420.50
    start = time.time()
    
    print(f"Starting MT5 EA Heartbeat Simulator to {url}...")
    
    while time.time() - start < duration_seconds:
        # Simulate slight market fluctuations in PnL
        pnl = round(320.30 + (random.random() * 20 - 10), 2)
        equity = round(balance + pnl, 2)
        margin = 640.0
        free_margin = round(equity - margin, 2)
        margin_level = round((equity / margin) * 100, 2)
        
        payload = {
            "account_number": 99887766,
            "server": "ICMarketsSC-Live",
            "currency": "USD",
            "balance": balance,
            "equity": equity,
            "margin": margin,
            "free_margin": free_margin,
            "margin_level": margin_level,
            "floating_pnl": pnl,
            "terminal_connected": True,
            "open_positions": 2,
            "timestamp": int(time.time())
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                pass
        except Exception as e:
            print(f"Heartbeat post error: {e}")
            
        time.sleep(1)

if __name__ == "__main__":
    run_simulation()
