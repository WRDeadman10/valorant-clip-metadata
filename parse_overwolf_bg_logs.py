import os
import glob
import json
import logging
import re
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

OVERWOLF_LOG_DIR = r"C:\Users\admin\AppData\Local\Overwolf\Log\Apps\Valorant Tracker"
CLIP_METADATA_DIR = "E:/New folder/Valorant Tracker/VALORANT"

class MatchState:
    def __init__(self):
        self.map_name = "Unknown"
        self.local_player_name = None
        self.local_agent = "Unknown"
        self.match_start = None
        self.match_end = None
    def __repr__(self):
        return f"<Match(start={self.match_start}, end={self.match_end}, map={self.map_name}, player={self.local_player_name}, agent={self.local_agent})>"

def parse_background_logs():
    log_files = glob.glob(os.path.join(OVERWOLF_LOG_DIR, "background.html*.log"))
    # Sort logs so we process them generally chronologically by modification time or file name index
    log_files.sort(key=os.path.getmtime)
    
    matches_timeline = []
    
    current_match = MatchState()
    
    for log_file in log_files:
        logging.info(f"Parsing Overwolf Log: {log_file}")
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if "match_info" not in line:
                        continue
                        
                    # Extract timestamp from log prefix (e.g. 2026-03-10 00:25:38,557)
                    timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
                    if not timestamp_match:
                        continue
                        
                    time_str = timestamp_match.group(1)
                    # Convert to datetime
                    try:
                        log_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S,%f")
                        # Overwolf logs are usually in local time, convert to naive or UTC if needed.
                        # Let's keep them as naive datetime to compare with the clip datetime logic which is usually local.
                    except ValueError:
                        continue
                    
                    if '"map":"' in line:
                        m = re.search(r'"map":"([^"]+)"', line)
                        if m:
                            val = m.group(1)
                            if val and val != "null":
                                # Handle Riot's internal map names like /Game/Maps/Triad/Triad
                                map_name = val.split('/')[-1]
                                current_match.map_name = map_name
                                if current_match.match_start is None:
                                    current_match.match_start = log_time

                    if "scoreboard" in line and '"is_local":true' in line:
                        # Extract name and character via regex to avoid multi-escape decode bugs
                        name_match = re.search(r'\\*"name\\*"\s*:\s*\\*"([^\\"]+)\\*"', line)
                        char_match = re.search(r'\\*"character\\*"\s*:\s*\\*"([^\\"]+)\\*"', line)
                        
                        if name_match and char_match:
                            current_match.local_player_name = name_match.group(1)
                            current_match.local_agent = char_match.group(1)
                            if current_match.match_start is None:
                                current_match.match_start = log_time
                            
                    # Match End (usually map goes null or session ends)
                    if '"map":null' in line and '"match_info"' in line:
                        if current_match.match_start is not None:
                            current_match.match_end = log_time
                            # Save the match timeline
                            matches_timeline.append(current_match)
                            current_match = MatchState() # Reset for next match

        except Exception as e:
            logging.error(f"Failed to read {log_file}: {e}")
            
    # Add any ongoing match
    if current_match.match_start is not None and current_match.match_end is None:
        # Just set end to way in the future or current time
        current_match.match_end = datetime.now()
        matches_timeline.append(current_match)

    logging.info(f"Found {len(matches_timeline)} match sessions in Overwolf logs.")
    for m in matches_timeline[-5:]:
        logging.info(f"  - {m}")
        
    return matches_timeline

def update_json_metadata():
    timeline = parse_background_logs()
    
    # Iterate dynamically over all mp4 files in the target directory
    video_files = glob.glob(os.path.join(CLIP_METADATA_DIR, "**", "*.mp4"), recursive=True)
    logging.info(f"Found {len(video_files)} mp4 clips to check against Overwolf logs.")
    
    updated_count = 0
    created_count = 0
    
    for v_path in video_files:
        try:
            clip_name = os.path.basename(v_path)
            
            # e.g VALORANT 03-04-2026 0-51-40-627.mp4 -> get timestamp
            m = re.search(r'VALORANT (\d{2}-\d{2}-\d{4} \d{1,2}-\d{2}-\d{2})', clip_name)
            if not m:
                continue
            
            time_str = m.group(1)
            clip_time = datetime.strptime(time_str, "%m-%d-%Y %H-%M-%S")
            
            # Find matching session
            matched_session = None
            for session in timeline:
                if session.match_start:
                    end_time = session.match_end if session.match_end else datetime.now()
                    
                    if session.match_start <= clip_time <= end_time:
                        matched_session = session
                        break
                        
            if not matched_session:
                continue
                
            # Check mapping dictionary for internal names -> pretty names if needed
            map_dict = {
                "Port": "Icebox", "Duality": "Bind", "Bonsai": "Split", "Ascent": "Ascent", 
                "Triad": "Haven", "Jam": "Lotus", "Juliett": "Sunset", "HURM": "Abyss", 
                "Pitt": "Pearl", "Foxtrot": "Breeze", "Canyon": "Fracture", "Venezia": "Ascent",
                "Jam": "Abyss", "Infinity": "TDM / Range"
            }
            # Character map dict if needed
            agent_dict = {
                "Vampire": "Reyna", "Hunter": "Sova", "Pandemic": "Viper", "Wraith": "Omen",
                "Gumshoe": "Cypher", "Breach": "Breach", "Clay": "Raze", "Thief": "Killjoy",
                "Stealth": "Yoru", "Rift": "Astra", "Grenadier": "KAY/O", "Deadeye": "Chamber",
                "Sprinter": "Neon", "BountyHunter": "Fade", "Mage": "Harbor", "AggroBot": "Gekko",
                "Cable": "Deadlock", "Sequoia": "Iso", "Smonk": "Clove", "Sarge": "Brimstone",
                "Wushu": "Jett", "Guide": "Skye", "Bling": "Chamber", "Phoenix": "Phoenix", "Sage": "Sage"
            }
            
            pretty_map = map_dict.get(matched_session.map_name, matched_session.map_name)
            pretty_agent = agent_dict.get(matched_session.local_agent, matched_session.local_agent)
            
            json_path = os.path.splitext(v_path)[0] + ".json"
            
            if os.path.exists(json_path):
                # Update existing JSON
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if not isinstance(data, dict):
                    continue
                
                needs_update = False
                if data.get("map") in ("Unknown", None) and pretty_map != "Unknown":
                    data["map"] = pretty_map
                    needs_update = True
                    
                if data.get("agent") in ("Unknown", None) and pretty_agent != "Unknown":
                    data["agent"] = pretty_agent
                    needs_update = True
                    
                if needs_update:
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
                    updated_count += 1
            else:
                # Create a new JSON for this video that had no metadata recorded!
                formatted_data = {
                    "clip": clip_name,
                    "match_id": "Unknown",
                    "map": pretty_map,
                    "agent": pretty_agent,
                    "kills": 0,
                    "round": -1,
                    "round_details": {}
                }
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(formatted_data, f, indent=4)
                created_count += 1
                
        except Exception as e:
            logging.error(f"Failed to process video {v_path}: {e}")

    logging.info(f"Finished. Updated {updated_count} existing JSONs. Created {created_count} missing JSONs.")

if __name__ == "__main__":
    update_json_metadata()
