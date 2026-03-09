import os
import requests
from typing import List, Dict, Any
from config import config

class HenrikDevClient:
    """
    Client for interacting with the HenrikDev Valorant API V3.
    This is preferred as it doesn't require a production Riot API key and returns pre-parsed structure.
    """
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or config.HENRIK_API_KEY
        
    def get_matches(self, region: str, name: str, tag: str, size: int = 5) -> List[Dict[Any, Any]]:
        """
        Fetches recent matches for a given player using HenrikDev API V3.
        region options: ap, na, eu, kr, latam, br
        Returns a list of parsed match dictionary objects.
        """
        url = config.HENRIK_API_BASE_URL.format(region=region, name=name, tag=tag)
        params = {"size": size}
        headers = {}
        if self.api_key:
            headers["Authorization"] = self.api_key
            
        print(f"Fetching matches from HenrikDev API for {name}#{tag} (Region: {region}, Size: {size})...")
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Henrik API Error: HTTP {response.status_code} - {response.text}")
            
        json_data = response.json()
        if json_data.get("status") != 200:
            raise Exception(f"Henrik API response error: {json_data.get('errors') or json_data}")
            
        return json_data.get("data", [])
