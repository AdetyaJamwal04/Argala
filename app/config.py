from typing import List
try:
    from pydantic import BaseSettings, Field
except ImportError:
    try:
        from pydantic.v1 import BaseSettings, Field
    except ImportError:
        from pydantic_settings import BaseSettings
        from pydantic import Field


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
    CORS_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://100.68.31.91:8000",
    ]
    
    # Operation mode
    DEBUG: bool = False

    class Config:
        case_sensitive = True


# Global settings singleton
settings = Settings()
