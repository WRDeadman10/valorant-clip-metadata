import os
from pydantic import BaseModel, Field

class Settings(BaseModel):
    """
    Configuration settings for the Valorant Clip Metadata project.
    """
    # API settings
    DEFAULT_API: str = Field(default="henrik", description="Default API to use: 'henrik' or 'riot'")
    
    # HenrikDev API settings
    HENRIK_API_BASE_URL: str = "https://api.henrikdev.xyz/valorant/v3/matches/{region}/{name}/{tag}"
    HENRIK_API_KEY: str | None = Field(default=None, description="Optional API key for HenrikDev API")
    
    # Riot API settings
    RIOT_API_BASE_URL: str = "https://{region}.api.riotgames.com/val/match/v1/matches/by-puuid/{puuid}"
    RIOT_API_KEY: str | None = Field(default=None, description="Required API key for Riot API")
    
    # Application settings
    CACHE_DIR: str = ".cache"
    SUPPORTED_VIDEO_FORMATS: list[str] = [".mp4", ".mkv", ".avi", ".webm"]

# Load configuration from environment variables if present
config = Settings(
    HENRIK_API_KEY="HDEV-58940747-b0aa-495a-9b68-44ee9cf2f030",
    RIOT_API_KEY="RGAPI-10cb5b4f-534c-4044-89a3-a04355ed14c2",
)
