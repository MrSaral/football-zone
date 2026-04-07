from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    This class handles all our environment variables.
    We're using pydantic-settings to automatically pull the API key from a .env file,
    ensuring we don't leak the API key accidentally.
    """

    # AIREVIEW: Consider adding field validation (e.g., min_length) to ensure key is present
    FOOTBALL_API_KEY: str
    FOOTBALL_BASE_URL: str = "https://api.football-data.org/v4/"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
