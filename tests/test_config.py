import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError
from config import Settings


def test_settings_load_from_env():
    """Test that settings can be loaded from environment variables."""
    test_env = {
        "FOOTBALL_API_KEY": "test_api_key_long",
        "FOOTBALL_BASE_URL": "https://test.api.com/v4/"
    }
    
    with patch.dict(os.environ, test_env):
        # We need to recreate the Settings instance to pull from the patched environment
        settings = Settings()
        assert settings.FOOTBALL_API_KEY == "test_api_key_long"
        assert settings.FOOTBALL_BASE_URL == "https://test.api.com/v4/"

def test_settings_default_base_url():
    """Test that settings have the correct default base URL."""
    test_env = {"FOOTBALL_API_KEY": "test_api_key_long"}
    with patch.dict(os.environ, test_env):
        settings = Settings()
        assert settings.FOOTBALL_BASE_URL == "https://api.football-data.org/v4/"

def test_settings_validation_error():
    """Test that a validation error is raised if the API key is too short."""
    test_env = {"FOOTBALL_API_KEY": "short"}
    with patch.dict(os.environ, test_env):
        with pytest.raises(ValidationError):
            Settings()
