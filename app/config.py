from typing import List
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """
    Gateway Configuration & Node Identity.
    Uses Pydantic v1 BaseSettings for full compatibility with Python 3.14 on 32-bit ARM.
    """
    GATEWAY_NAME: str = "Argala-Gateway"
    NODE_ID: str = "android-termux-node-01"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Security: Inbound API Key for authenticating agent requests
    API_KEY: str = Field(default="argala-dev-key-change-me", env="GATEWAY_API_KEY")
    LEGACY_API_KEY: str = "aegis-edge-dev-key-change-me"

    
    # Allowed origins for web dashboards and cross-origin agents
    CORS_ORIGINS: List[str] = ["*"]
    
    # Operation mode
    DEBUG: bool = False

    class Config:
        case_sensitive = True


# Global settings singleton
settings = Settings()
