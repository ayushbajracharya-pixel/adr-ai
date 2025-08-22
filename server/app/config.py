from pydantic_settings import BaseSettings 

class Settings(BaseSettings):
    app_name: str = "ADR AI Server"
    app_debug: bool = False

    class Config:
        env_file = ".env"   # load from .env automatically

settings = Settings()
