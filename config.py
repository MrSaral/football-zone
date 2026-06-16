from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    This class handles all our environment variables.
    We're using pydantic-settings to automatically pull the API key from a .env file,
    ensuring we don't leak the API key accidentally.
    """

    FOOTBALL_API_KEY: str = Field(..., min_length=10, description="API Key for football-data.org")
    FOOTBALL_BASE_URL: str = "https://api.football-data.org/v4/"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
