from datetime import datetime, timezone
from typing import Dict, Any, List

from config import config

# Map URL endpoints to basic map strings for Riot API fallback (HenrikDev directly provides actual strings)
RIOT_MAP_IDS = {
    "/Game/Maps/Ascent/Ascent": "Ascent",
    "/Game/Maps/Bonsai/Bonsai": "Split",
    "/Game/Maps/Canyon/Canyon": "Fracture",
    "/Game/Maps/Duality/Duality": "Bind",
    "/Game/Maps/Foxtrot/Foxtrot": "Breeze",
    "/Game/Maps/HURM/HURM": "Abyss",
    "/Game/Maps/Jam/Jam": "Lotus",
    "/Game/Maps/Juliett/Juliett": "Sunset",
    "/Game/Maps/Pitt/Pitt": "Pearl",
    "/Game/Maps/Port/Port": "Icebox",
    "/Game/Maps/Triad/Triad": "Haven",
}

class MatchParser:
    """
    Parses complex match objects from either HenrikDev or Riot APIs and matches 
    them to a specific timestamp (the clip recording time).
    """
    def __init__(self, api_type: str | None = None):
        self.api_type = api_type or config.DEFAULT_API
        
    def _parse_henrik_match(self, match: dict, player_name: str, player_tag: str) -> Dict[str, Any] | None:
        """Parses HenrikDev V3 API match data."""
        metadata = match.get("metadata") or {}
        if not metadata:
            return None
        match_id = metadata.get("matchid", "Unknown")
        map_name = metadata.get("map", "Unknown")
        
        game_start_unix = metadata.get("game_start", 0)       # Delivered in seconds
        game_length_s = metadata.get("game_length", 0)        # Delivered in seconds
        
        start_dt = datetime.fromtimestamp(game_start_unix, tz=timezone.utc)
        end_dt = datetime.fromtimestamp(game_start_unix + game_length_s, tz=timezone.utc)
        
        agent = "Unknown"
        kills = 0
        
        # Locate target player within the match participants
        all_players = match.get("players", {}).get("all_players", [])
        for p in all_players:
            if p.get("name", "").lower() == player_name.lower() and p.get("tag", "").lower() == player_tag.lower():
                agent = p.get("character", "Unknown")
                kills = p.get("stats", {}).get("kills", 0)
                break
                
        # Extract round kills information
        player_kills = []
        all_kills = []
        for k in match.get("kills", []):
            round_num = k.get("round", 0)
            time_ms = k.get("kill_time_in_match", 0)
            all_kills.append({"round": round_num, "time": time_ms})
            
            killer_name = k.get("killer_display_name", "")
            # HenrikDev killer_display_name contains Name#Tag
            if f"{player_name.lower()}#" in killer_name.lower() or player_name.lower() in killer_name.lower():
                player_kills.append({"round": round_num, "time": time_ms})
                
        return {
            "match_id": match_id,
            "map": map_name,
            "agent": agent,
            "kills": kills, # Total matches kills
            "player_kills": player_kills,
            "all_kills": all_kills,
            "start_time": start_dt,
            "end_time": end_dt
        }
        
    def _parse_riot_match(self, match: dict, player_name: str, player_tag: str) -> Dict[str, Any] | None:
        """Parses official Riot API Match-V1 data structure."""
        match_info = match.get("matchInfo") or {}
        if not match_info:
            return None
        match_id = match_info.get("matchId", "Unknown")
        map_url = match_info.get("mapId", "")
        
        # Convert internal map URL to human readable map name where possible
        map_name = RIOT_MAP_IDS.get(map_url, map_url)
        
        game_start_ms = match_info.get("gameStartMillis", 0)
        game_length_ms = match_info.get("gameLengthMillis", 0)
        
        start_dt = datetime.fromtimestamp(game_start_ms / 1000.0, tz=timezone.utc)
        end_dt = datetime.fromtimestamp((game_start_ms + game_length_ms) / 1000.0, tz=timezone.utc)
        
        # Note: True Riot API translation of character IDs requires querying the separate Valorant-API.
        agent = "Unknown (Riot UUID)"
        kills = 0
        
        # Locate target player within the root players payload
        players = match.get("players", [])
        for p in players:
            if p.get("gameName", "").lower() == player_name.lower() and p.get("tagLine", "").lower() == player_tag.lower():
                agent = p.get("characterId", "Unknown (Riot UUID)")
                kills = p.get("stats", {}).get("kills", 0)
                break
                
        # Extract round kills information for Riot API
        player_kills = []
        all_kills = []
        for k in match.get("kills", []):
            round_num = k.get("roundNum", 0)
            time_ms = k.get("timeSinceGameStartMillis", 0)
            all_kills.append({"round": round_num, "time": time_ms})
            
            killer = k.get("killer", "")
            # We would need to match PUUID in Riot API, but we'll try basic string fallback if possible 
            # (Riot API Match-V1 `kills` list contains PUUIDs, so we'd need to map it)
            # Find the target player's PUUID first
            target_puuid = None
            for p in players:
                if p.get("gameName", "").lower() == player_name.lower() and p.get("tagLine", "").lower() == player_tag.lower():
                    target_puuid = p.get("puuid")
                    break
                    
            if target_puuid and killer == target_puuid:
                player_kills.append({"round": round_num, "time": time_ms})
                
        return {
            "match_id": match_id,
            "map": map_name,
            "agent": agent,
            "kills": kills, # Total match kills
            "player_kills": player_kills,
            "all_kills": all_kills,
            "start_time": start_dt,
            "end_time": end_dt
        }
        
    def find_match_for_clip(self, clip_timestamp: datetime, matches: List[Dict[Any, Any]], player_name: str, player_tag: str) -> Dict[str, Any] | None:
        """
        Given a list of fetched match payloads, maps a physical video clip timestamp to the exact 
        round or game if the clip creation time falls within that match's duration.
        """
        for match in matches:
            if self.api_type == "riot":
                parsed = self._parse_riot_match(match, player_name, player_tag)
            else:
                parsed = self._parse_henrik_match(match, player_name, player_tag)
                
            if not parsed:
                continue
                
            start = parsed["start_time"]
            end = parsed["end_time"]
            
            # Clips are typically created/saved around the end of a match or slightly after.
            # Add a 600-second buffer (10 minutes) post match-end to capture late-saved clips.
            # We check if clip was created between (start, end+10mins).
            buffer_seconds = 600
            end_with_buffer = datetime.fromtimestamp(end.timestamp() + buffer_seconds, tz=timezone.utc)
            
            if start <= clip_timestamp <= end_with_buffer:
                # Calculate round-specific kills
                clip_kills = parsed["kills"] # Default to total match kills
                clip_round = -1 # Default unknown round
                
                if parsed["all_kills"]:
                    # Tracker Network saves clips typically 60-90s AFTER the highlight (e.g., end of round)
                    # We want to find the closest kill that happened BEFORE the clip was saved.
                    def find_closest_round(kill_list, max_allowed_diff=180):
                        best_round = None
                        min_err = float("inf")
                        for k in kill_list:
                            kill_dt = datetime.fromtimestamp(start.timestamp() + (k["time"] / 1000.0), tz=timezone.utc)
                            diff = (clip_timestamp - kill_dt).total_seconds()
                            
                            # The kill should happen BEFORE the clip timestamp.
                            # Allow a tiny 15-second grace period for clock drift.
                            if diff >= -15:
                                abs_diff = abs(diff)
                                if abs_diff < min_err:
                                    min_err = abs_diff
                                    best_round = k["round"]
                        
                        if min_err <= max_allowed_diff:
                            return best_round
                        return None
                        
                    # 1. Look for a PLAYER highlight first
                    closest_round = find_closest_round(parsed["player_kills"], max_allowed_diff=180)
                    
                    # 2. Fallback to ANY kill if the player didn't get a kill recently
                    if closest_round is None:
                        closest_round = find_closest_round(parsed["all_kills"], max_allowed_diff=180)
                        
                        
                    if closest_round is not None:
                        # Count how many player kills were in that specific round
                        clip_round = closest_round
                        clip_kills = sum(1 for pk in parsed["player_kills"] if pk["round"] == closest_round)
                        
                        # Extract deep round details if we have raw henrik match format
                        round_details = {}
                        if "rounds" in match and 0 <= clip_round < len(match["rounds"]):
                            round_data = match["rounds"][clip_round]
                            for ps in round_data.get("player_stats", []):
                                p_name = ps.get("player_display_name", "").lower()
                                if player_name.lower() in p_name:
                                    # This is our player's stats for the round
                                    detailed_kills = []
                                    for ke in ps.get("kill_events", []):
                                        v_puuid = ke.get("victim_puuid")
                                        
                                        # Look up victim agent
                                        v_agent = "Unknown"
                                        for p in match.get("players", {}).get("all_players", []):
                                            if p.get("puuid") == v_puuid:
                                                v_agent = p.get("character", "Unknown")
                                                break
                                                
                                        # Find specific damage applied to this victim to get headshot stats
                                        hs, bs, dmg = 0, 0, 0
                                        for de in ps.get("damage_events", []):
                                            if de.get("receiver_puuid") == v_puuid:
                                                hs += de.get("headshots", 0)
                                                bs += de.get("bodyshots", 0)
                                                dmg += de.get("damage", 0)
                                                
                                        detailed_kills.append({
                                            "victim": ke.get("victim_display_name", "Unknown"),
                                            "victim_agent": v_agent,
                                            "weapon": ke.get("damage_weapon_name", "Unknown"),
                                            "damage_dealt": dmg,
                                            "headshots": hs,
                                            "bodyshots": bs
                                        })
                                        
                                    round_details = {
                                        "total_damage_dealt": ps.get("damage", 0),
                                        "total_headshots": ps.get("headshots", 0),
                                        "kills_breakdown": detailed_kills
                                    }
                                    break
                        
                # Overwrite total kills with round-specific kills
                parsed["kills"] = clip_kills
                parsed["round"] = clip_round + 1 if clip_round != -1 else -1 # Store as 1-indexed for display
                parsed["round_details"] = round_details if 'round_details' in locals() else {}
                parsed["_raw_match"] = match
                return parsed
                
        return None
