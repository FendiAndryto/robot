import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.bridge_service import bridge_service
from app.services.strategy_engine import strategy_engine
from app.core.security import create_access_token

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    bridge_service.reset_state()
    strategy_engine.reset_state()
    yield
    bridge_service.reset_state()
    strategy_engine.reset_state()


def get_auth_headers(username: str = "admin") -> dict:
    token = create_access_token(subject=username)
    return {"Authorization": f"Bearer {token}"}


def test_calculate_ema_math():
    prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0]
    ema_5 = strategy_engine.calculate_ema(prices, 5)
    assert len(ema_5) == 6
    # First value should be SMA of first 5: (10+11+12+13+14)/5 = 12.0
    assert ema_5[0] == 12.0
    # Multiplier for 5 is 2 / (5 + 1) = 1/3
    # Second EMA: 15.0 * (1/3) + 12.0 * (2/3) = 5.0 + 8.0 = 13.0
    assert abs(ema_5[1] - 13.0) < 1e-4


def test_calculate_rsi_math():
    # Continual upward prices should yield high RSI (above 70)
    up_prices = [float(i) for i in range(100, 125)]
    rsi_up = strategy_engine.calculate_rsi(up_prices, 14)
    assert len(rsi_up) > 0
    assert rsi_up[-1] >= 90.0

    # Continual downward prices should yield low RSI (below 30)
    down_prices = [float(i) for i in range(125, 100, -1)]
    rsi_down = strategy_engine.calculate_rsi(down_prices, 14)
    assert len(rsi_down) > 0
    assert rsi_down[-1] <= 10.0


def test_evaluate_candles_confluence():
    # Build a simulated uptrend series where Fast EMA > Slow EMA and RSI ~ 56.9 (healthy bullish momentum)
    candles = []
    price = 1.08000
    for i in range(35):
        step = 0.00010 if (i % 2 == 0) else -0.00008
        price += step
        candles.append({
            "time": 1700000000 + (i * 60),
            "open": round(price - 0.00005, 5),
            "high": round(price + 0.0001, 5),
            "low": round(price - 0.0001, 5),
            "close": round(price, 5),
            "volume": 100.0
        })

    resp = client.post("/api/v1/strategy/evaluate-candles?symbol=EURUSD", json=candles)
    assert resp.status_code == 200
    data = resp.json()
    assert data is not None
    assert data["symbol"] == "EURUSD"
    assert data["action"] == "BUY"
    assert data["status"] == "PENDING"
    assert data["sl"] < data["entry_price"]
    assert data["tp"] > data["entry_price"]
    assert data["recommended_lot"] >= 0.01
    assert data["symbol"] == "EURUSD"
    assert data["action"] == "BUY"
    assert data["status"] == "PENDING"
    assert data["sl"] < data["entry_price"]
    assert data["tp"] > data["entry_price"]
    assert data["recommended_lot"] >= 0.01


def test_generate_test_signal_and_list():
    auth_headers = get_auth_headers("admin")

    # Generate a BUY test signal
    payload = {
        "symbol": "GBPUSD",
        "action": "BUY",
        "price": 1.29500,
        "sl_pips": 30.0,
        "rr_ratio": 2.0
    }
    gen_resp = client.post("/api/v1/strategy/generate-test-signal", json=payload, headers=auth_headers)
    assert gen_resp.status_code == 200
    sig = gen_resp.json()
    assert sig["symbol"] == "GBPUSD"
    assert sig["action"] == "BUY"
    assert sig["entry_price"] == 1.29500
    assert sig["sl"] == round(1.29500 - (30.0 * 0.0001), 5)
    assert sig["tp"] == round(1.29500 + (60.0 * 0.0001), 5)
    assert sig["status"] == "PENDING"

    # Verify signal appears in GET /api/v1/strategy/signals
    list_resp = client.get("/api/v1/strategy/signals")
    assert list_resp.status_code == 200
    signals = list_resp.json()
    assert len(signals) == 1
    assert signals[0]["signal_id"] == sig["signal_id"]


def test_approve_signal_disabled_on_api_and_works_internally():
    auth_headers = get_auth_headers("admin")

    # 1. Create a test signal
    gen_resp = client.post("/api/v1/strategy/generate-test-signal", json={
        "symbol": "XAUUSD",
        "action": "BUY",
        "price": 2720.50
    }, headers=auth_headers)
    assert gen_resp.status_code == 200
    signal_id = gen_resp.json()["signal_id"]

    # 2. Web API approve must be rejected with 403 Forbidden (Full-Auto trading only)
    approve_resp = client.post(
        f"/api/v1/strategy/signals/{signal_id}/approve",
        json={"custom_lot": 0.25},
        headers=auth_headers
    )
    assert approve_resp.status_code == 403
    assert "Semi-auto signal approval is disabled" in approve_resp.json()["detail"]

    # 3. Strategy engine internally can auto-execute the signal (as AutoPilot does)
    from app.services.strategy_engine import strategy_engine
    exec_res = strategy_engine.approve_signal(signal_id=signal_id, custom_lot=0.25)
    assert exec_res["status"] == "approved"
    assert exec_res["signal"].status == "APPROVED"

    # 4. Verify order was queued to bridge
    hb_resp = client.post("/api/v1/bridge/heartbeat", json={
        "account_number": 12345,
        "server": "Demo",
        "currency": "USD",
        "balance": 10000.0,
        "equity": 10000.0,
        "timestamp": int(time.time())
    })
    assert hb_resp.status_code == 200
    commands = hb_resp.json()["commands"]
    assert len(commands) == 1
    assert commands[0]["action"] == "BUY"
    assert commands[0]["symbol"] == "XAUUSD"
    assert commands[0]["volume"] == 0.25


def test_dismiss_signal():
    auth_headers = get_auth_headers("admin")

    # Create signal
    gen_resp = client.post("/api/v1/strategy/generate-test-signal", json={"symbol": "USDJPY"}, headers=auth_headers)
    signal_id = gen_resp.json()["signal_id"]

    # Dismiss signal
    dismiss_resp = client.post(
        f"/api/v1/strategy/signals/{signal_id}/dismiss",
        json={"reason": "High spread during Asian session"},
        headers=auth_headers
    )
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.json()["status"] == "dismissed"

    # Verify pending list is now empty
    pending_list = client.get("/api/v1/strategy/signals").json()
    assert len(pending_list) == 0

    # Verify all signals list shows it with DISMISSED status
    all_list = client.get("/api/v1/strategy/signals?all=true").json()
    assert len(all_list) == 1
    assert all_list[0]["status"] == "DISMISSED"


def test_strategy_auth_guards():
    # Attempting to approve -> 403 Forbidden (disabled)
    resp = client.post("/api/v1/strategy/signals/fake_id/approve")
    assert resp.status_code == 403

    # Attempting to dismiss without auth -> 401
    resp = client.post("/api/v1/strategy/signals/fake_id/dismiss")
    assert resp.status_code == 401


def test_scalping_spread_guard_blocks_signal():
    candles = []
    price = 1.08000
    for i in range(35):
        step = 0.00010 if (i % 2 == 0) else -0.00008
        price += step
        candles.append({
            "time": 1700000000 + (i * 60),
            "open": round(price - 0.00005, 5),
            "high": round(price + 0.0001, 5),
            "low": round(price - 0.0001, 5),
            "close": round(price, 5),
            "volume": 100.0
        })

    # High spread (e.g. 60 points > max 35) must block entry
    sig = strategy_engine.evaluate_candles(
        candles=candles,
        symbol="EURUSD",
        current_spread=60,
        ignore_session_filter=True
    )
    assert sig is None

    # Low spread (e.g. 15 points <= 35) should succeed
    sig_ok = strategy_engine.evaluate_candles(
        candles=candles,
        symbol="EURUSD",
        current_spread=15,
        ignore_session_filter=True
    )
    assert sig_ok is not None
    assert sig_ok.action == "BUY"

    # XAUUSD: 200 points is normal and should pass (< 350 max)
    strategy_engine.reset_state()
    sig_gold = strategy_engine.evaluate_candles(
        candles=candles,
        symbol="XAUUSD",
        current_spread=200,
        ignore_session_filter=True
    )
    assert sig_gold is not None

    # XAUUSD: 400 points is abnormal and should be blocked (> 350 max)
    strategy_engine.reset_state()
    sig_gold_high = strategy_engine.evaluate_candles(
        candles=candles,
        symbol="XAUUSD",
        current_spread=400,
        ignore_session_filter=True
    )
    assert sig_gold_high is None


def test_scalping_m5_confluence():
    m15_candles = []
    price = 1.08000
    for i in range(35):
        step = 0.00010 if (i % 2 == 0) else -0.00008
        price += step
        m15_candles.append({
            "time": 1700000000 + (i * 900),
            "open": round(price - 0.00005, 5),
            "high": round(price + 0.0001, 5),
            "low": round(price - 0.0001, 5),
            "close": round(price, 5),
            "volume": 100.0
        })

    # M5 series also in strong bullish alignment
    m5_candles = []
    price_m5 = 1.08000
    for i in range(30):
        step = 0.00008 if (i % 2 == 0) else -0.00005
        price_m5 += step
        m5_candles.append({
            "time": 1700000000 + (i * 300),
            "open": round(price_m5 - 0.00003, 5),
            "high": round(price_m5 + 0.00008, 5),
            "low": round(price_m5 - 0.00005, 5),
            "close": round(price_m5, 5),
            "volume": 50.0
        })

    sig = strategy_engine.evaluate_candles(
        candles=m15_candles,
        symbol="EURUSD",
        candles_m5=m5_candles,
        current_spread=12,
        ignore_session_filter=True
    )
    assert sig is not None
    assert sig.action == "BUY"
    # Verify scalping SL is 15 pips
    expected_sl = round(sig.entry_price - (15.0 * 0.0001), 5)
    assert abs(sig.sl - expected_sl) < 1e-4

