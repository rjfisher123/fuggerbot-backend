"""
Application settings using pydantic-settings.

Loads configuration from environment variables with validation.
"""
import os
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Uses pydantic-settings to load from .env file or environment variables.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra env vars
    )
    
    # OpenRouter API Configuration
    openrouter_api_key: str = Field(
        ...,
        description="OpenRouter API key for DeepSeek/LLM access",
        validation_alias="OPENROUTER_API_KEY"
    )
    
    # DeepSeek Model Configuration
    deepseek_model: str = Field(
        default="deepseek/deepseek-r1",
        description="DeepSeek model identifier",
        validation_alias="DEEPSEEK_MODEL"
    )
    
    # Environment State
    env_state: Literal["dev", "prod"] = Field(
        default="dev",
        description="Environment state: 'dev' or 'prod'",
        validation_alias="ENV_STATE"
    )
    
    @field_validator("openrouter_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """
        Validate that API key is provided and not a placeholder.
        
        Raises:
            ValueError: If API key is missing or appears to be a placeholder
        """
        if not v or not v.strip():
            raise ValueError(
                "OPENROUTER_API_KEY is required but not set. "
                "Please set it in your .env file or environment variables. "
                "Get your API key from https://openrouter.ai/"
            )
        
        # Check for common placeholder values
        placeholder_values = [
            "your_api_key_here",
            "sk-placeholder",
            "your_openrouter_api_key",
            "replace_with_your_key",
            ""
        ]
        
        if v.strip().lower() in [p.lower() for p in placeholder_values]:
            raise ValueError(
                f"OPENROUTER_API_KEY appears to be a placeholder value: '{v}'. "
                "Please set a valid API key in your .env file. "
                "Get your API key from https://openrouter.ai/"
            )
        
        # Basic format check (OpenRouter keys typically start with 'sk-' or similar)
        if len(v.strip()) < 10:
            raise ValueError(
                f"OPENROUTER_API_KEY appears to be invalid (too short). "
                "Please verify your API key is correct."
            )
        
        return v.strip()
    
    @field_validator("env_state")
    @classmethod
    def validate_env_state(cls, v: str) -> str:
        """Validate environment state is 'dev' or 'prod'."""
        v_lower = v.lower().strip()
        if v_lower not in ["dev", "prod"]:
            raise ValueError(
                f"ENV_STATE must be 'dev' or 'prod', got: '{v}'. "
                "Please set ENV_STATE=dev or ENV_STATE=prod in your .env file."
            )
        return v_lower
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.env_state == "prod"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.env_state == "dev"
    
    def __repr__(self) -> str:
        """Safe representation that doesn't expose API key."""
        return (
            f"Settings("
            f"deepseek_model='{self.deepseek_model}', "
            f"env_state='{self.env_state}', "
            f"openrouter_api_key='***'"
            f")"
        )


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get or create global settings instance.
    
    Returns:
        Settings instance with loaded configuration
        
    Raises:
        ValueError: If required settings (like API key) are missing or invalid
    """
    global _settings
    
    if _settings is None:
        try:
            _settings = Settings()
        except Exception as e:
            # Provide helpful error message
            error_msg = str(e)
            if "OPENROUTER_API_KEY" in error_msg or "openrouter_api_key" in error_msg:
                raise ValueError(
                    "❌ OPENROUTER_API_KEY is required but not set or invalid.\n\n"
                    "To fix this:\n"
                    "1. Create a .env file in the project root (or copy env_template.txt)\n"
                    "2. Add: OPENROUTER_API_KEY=your_actual_api_key_here\n"
                    "3. Get your API key from: https://openrouter.ai/\n\n"
                    f"Original error: {error_msg}"
                ) from e
            raise
    
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment (useful for testing or after .env changes).
    
    Returns:
        New Settings instance
    """
    global _settings
    _settings = None
    return get_settings()

