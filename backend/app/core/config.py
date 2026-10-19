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
