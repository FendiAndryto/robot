from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Robot Trading MT5 Bridge"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = "default_insecure_secret_key_change_in_production"
    ALLOWED_HOSTS: str = "*"
    
    MT5_MAGIC_NUMBER: int = 778899
    HEARTBEAT_TIMEOUT_SECONDS: int = 10
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    @property
    def cors_origins(self) -> List[str]:
        if self.ALLOWED_HOSTS == "*":
            return ["*"]
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",")]


settings = Settings()
