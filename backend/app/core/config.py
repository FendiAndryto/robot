from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Robot Trading MT5 Bridge"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = "default_insecure_secret_key_change_in_production"
    ALLOWED_HOSTS: str = "*"
    
    CORS_ORIGINS: str = ""
    
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change_this_password"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_ALGORITHM: str = "HS256"
    
    MT5_MAGIC_NUMBER: int = 778899
    BRIDGE_POLL_INTERVAL_MS: int = 500
    HEARTBEAT_TIMEOUT_SECONDS: int = 10
    
    # Risk Management Defaults
    DEFAULT_RISK_PER_TRADE_PERCENT: float = 1.0
    MAX_RISK_PER_TRADE_PERCENT: float = 10.0
    MAX_DAILY_DRAWDOWN_PERCENT: float = 3.0
    MAX_SPREAD_POINTS: int = 35
    MIN_LOT_SIZE: float = 0.01
    MAX_LOT_SIZE: float = 100.0

    # Scalping & Day Trading Strategy Engine Defaults
    STRATEGY_ENABLED: bool = True
    STRATEGY_EMA_FAST: int = 9
    STRATEGY_EMA_SLOW: int = 21
    STRATEGY_RSI_PERIOD: int = 14
    STRATEGY_RSI_OVERSOLD: float = 32.0
    STRATEGY_RSI_OVERBOUGHT: float = 68.0
    STRATEGY_DEFAULT_SL_PIPS: float = 15.0
    STRATEGY_DEFAULT_RR_RATIO: float = 1.8
    STRATEGY_SIGNAL_TTL_SECONDS: int = 300
    STRATEGY_MONITORED_SYMBOLS: str = "EURUSD,GBPUSD,USDJPY,XAUUSD"
    STRATEGY_ENABLE_SESSION_FILTER: bool = True
    STRATEGY_SESSION_START_HOUR_UTC: int = 6   # 13:00 WIB (London Open)
    STRATEGY_SESSION_END_HOUR_UTC: int = 21    # 04:00 WIB (Before Rollover Blackout)
    STRATEGY_MAX_CONCURRENT_POSITIONS_PER_SYMBOL: int = 1

    # Auto-Pilot Mode & Drawdown Guard
    AUTOPILOT_DEFAULT_ENABLED: bool = False
    AUTOPILOT_MAX_DAILY_TRADES: int = 20
    AUTOPILOT_RESET_HOUR_UTC: int = 0
    AUTOPILOT_USE_FIXED_LOT: bool = True
    AUTOPILOT_FIXED_LOT_SIZE: float = 0.01

    # Telegram Push Notifications
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_NOTIFICATIONS_ENABLED: bool = True
    
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    @property
    def cors_origins(self) -> List[str]:
        base_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://localhost:8089",
        ]
        if self.CORS_ORIGINS:
            custom = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
            base_origins.extend(custom)
            
        if self.ALLOWED_HOSTS and self.ALLOWED_HOSTS != "*":
            for host in self.ALLOWED_HOSTS.split(","):
                h = host.strip()
                if h:
                    if not h.startswith("http://") and not h.startswith("https://"):
                        base_origins.append(f"http://{h}")
                        base_origins.append(f"http://{h}:5173")
                        base_origins.append(f"http://{h}:3000")
                    else:
                        base_origins.append(h)
                        
        return list(dict.fromkeys(base_origins))


settings = Settings()
