import json
from typing import List, Dict, Any
from pathlib import Path

from config import config
from api.henrik_client import HenrikDevClient
from api.riot_client import RiotAPIClient

class MatchFetcher:
    """
    Orchestrates fetching matches and implements a file-based caching mechanism 
    to prevent spamming external APIs on successive runs.
    """
    def __init__(self, api_type: str | None = None):
        self.api_type = api_type or config.DEFAULT_API
        
        # Ensure cache directory exists
        self.cache_dir = Path(config.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        if self.api_type == "riot":
            self.client = RiotAPIClient()
        else:
            self.client = HenrikDevClient()
            
    def _get_cache_path(self, region: str, name: str, tag: str) -> Path:
        """
        Generates a valid filename for caching a player's matches.
        """
        sanitized_name = f"{name}_{tag}_{region}".replace(" ", "_").replace("/", "_")
        return self.cache_dir / f"{sanitized_name}_{self.api_type}_matches.json"
        
    def fetch_matches(self, region: str, name: str, tag: str, force_refresh: bool = False, size: int = 15) -> List[Dict[Any, Any]]:
        """
        Fetches matches using the configured API client, or retrieves from cache 
        if previously fetched (and not forced to refresh).
        """
        cache_path = self._get_cache_path(region, name, tag)
        
        # Return existing cache file contents if younger than 1 hour
        if not force_refresh and cache_path.exists():
            import time
            file_age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
            
            if file_age_hours < 1.0:
                print(f"Loading matches for {name}#{tag} from local cache...")
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"Local cache for {name}#{tag} is older than 1 hour. Refreshing...")
                
        # Fetch directly from API
        matches = self.client.get_matches(region, name, tag, size=size)
        
        # Save fresh results to cache
        print(f"Saving newly fetched matches to local cache...")
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(matches, f, indent=4)
            
        return matches
