import os
import requests
from typing import List, Dict, Any
from config import config

class RiotAPIClient:
    """
    Client for interacting with the official Riot Games Valorant APIs.
    Requires a valid RSO developer API key.
    """
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or config.RIOT_API_KEY
        if not self.api_key:
            raise ValueError("Riot API requires an API key in config or environment. Set RIOT_API_KEY.")
        self.headers = {"X-Riot-Token": self.api_key}
        
    def _get_account_region(self, val_region: str) -> str:
        """
        Maps Valorant region to Riot account region (required for PUUID lookup).
        """
        val_region = val_region.lower()
        if val_region in ['na', 'br', 'latam']:
            return 'americas'
        if val_region in ['eu']:
            return 'europe'
        if val_region in ['ap', 'kr']:
            return 'asia'
        return 'americas' # Default fallback

    def get_puuid(self, name: str, tag: str, val_region: str) -> str:
        """
        Retrieves a player's PUUID from their Riot ID.
        """
        account_region = self._get_account_region(val_region)
        url = f"https://{account_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
        
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            raise Exception(f"Riot API - Failed to fetch PUUID: {resp.status_code} - {resp.text}")
            
        return resp.json()["puuid"]
        
    def get_matchlist(self, puuid: str, region: str) -> List[str]:
        """
        Retrieves recent match IDs for a specific PUUID.
        """
        url = config.RIOT_API_BASE_URL.format(region=region.lower(), puuid=puuid)
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            raise Exception(f"Riot API - Failed to fetch matchlist: {resp.status_code} - {resp.text}")
            
        data = resp.json()
        return [match["matchId"] for match in data.get("history", [])]
        
    def get_match(self, match_id: str, region: str) -> Dict[Any, Any]:
        """
        Retrieves specific match details using a match ID.
        """
        url = f"https://{region.lower()}.api.riotgames.com/val/match/v1/matches/{match_id}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            raise Exception(f"Riot API - Failed to fetch match {match_id}: {resp.status_code} - {resp.text}")
        return resp.json()
        
    def get_matches(self, region: str, name: str, tag: str, size: int = 5) -> List[Dict[Any, Any]]:
        """
        Orchestrates fetching full match details for recent matches.
        """
        print(f"Fetching matches from Riot API for {name}#{tag} (Region: {region})...")
        puuid = self.get_puuid(name, tag, region)
        match_ids = self.get_matchlist(puuid, region)
        
        matches = []
        # Only take the first `size` matches to minimize requests
        for mid in match_ids[:size]:
            matches.append(self.get_match(mid, region))
            
        return matches
