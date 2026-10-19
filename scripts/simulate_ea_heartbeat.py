import time
import json
import urllib.request
import random

def run_simulation(duration_seconds=300):
    url = "http://127.0.0.1:8089/api/v1/bridge/heartbeat"
    balance = 25420.50
    start = time.time()
    
    # Active open positions list
    positions = [
        {
            "ticket": 789101,
            "symbol": "EURUSD",
            "type": "BUY",
            "volume": 0.05,
            "open_price": 1.08520,
            "current_price": 1.08640,
            "sl": 1.08000,
            "tp": 1.09500,
            "pnl": 60.00,
            "open_time": int(time.time() - 3600),
            "magic": 778899
        }
    ]
    
    ticket_counter = 800000
    print(f"Starting MT5 EA Heartbeat & Execution Simulator to {url}...")
    
    while time.time() - start < duration_seconds:
        # Calculate dynamic floating PnL
        total_pnl = 0.0
        for p in positions:
            fluct = round((random.random() * 2 - 1) * 2.0, 2)
            p["pnl"] = round(p["pnl"] + fluct, 2)
            p["current_price"] = round(p["open_price"] + (0.0001 if p["type"] == "BUY" else -0.0001) * (p["pnl"] / 5), 5)
            total_pnl += p["pnl"]
            
        total_pnl = round(total_pnl, 2)
        equity = round(balance + total_pnl, 2)
        margin = round(len(positions) * 200.0, 2)
        free_margin = round(equity - margin, 2)
        margin_level = round((equity / margin) * 100, 2) if margin > 0 else 0.0
        
        payload = {
            "account_number": 99887766,
            "server": "ICMarketsSC-Live",
            "currency": "USD",
            "balance": balance,
            "equity": equity,
            "margin": margin,
            "free_margin": free_margin,
            "margin_level": margin_level,
            "floating_pnl": total_pnl,
            "terminal_connected": True,
            "open_positions": len(positions),
            "positions": positions,
            "timestamp": int(time.time())
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                resp_data = json.loads(resp.read().decode())
                commands = resp_data.get("commands", [])
                
                for cmd in commands:
                    action = cmd.get("action")
                    cmd_id = cmd.get("command_id")
                    print(f">>> [Simulator] Executing command {action} ({cmd_id})...")
                    
                    if action in ("BUY", "SELL"):
                        ticket_counter += 1
                        new_pos = {
                            "ticket": ticket_counter,
                            "symbol": cmd.get("symbol", "EURUSD"),
                            "type": action,
                            "volume": cmd.get("volume", 0.01),
                            "open_price": 1.08500 if "EUR" in cmd.get("symbol", "") else 2720.00,
                            "current_price": 1.08500 if "EUR" in cmd.get("symbol", "") else 2720.00,
                            "sl": cmd.get("sl") or 0.0,
                            "tp": cmd.get("tp") or 0.0,
                            "pnl": 0.00,
                            "open_time": int(time.time()),
                            "magic": 778899
                        }
                        positions.append(new_pos)
                        print(f">>> [Simulator] Opened new position #{ticket_counter} {action} {new_pos['symbol']}")
                    elif action == "CLOSE":
                        target_ticket = cmd.get("ticket")
                        positions = [p for p in positions if p["ticket"] != target_ticket]
                        print(f">>> [Simulator] Closed position #{target_ticket}")
                    elif action == "CLOSE_ALL":
                        positions.clear()
                        print(">>> [Simulator] Closed ALL positions")
        except Exception as e:
            print(f"Heartbeat post error: {e}")
            
        time.sleep(1)

if __name__ == "__main__":
    run_simulation()
