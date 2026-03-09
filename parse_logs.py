import json
import os
import glob
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SCANNED_FOLDERS_FILE = "scanned_folders.json"
LOG_DIR = "Logs"

def load_scanned_folders():
    if not os.path.exists(SCANNED_FOLDERS_FILE):
        logging.error(f"Could not find {SCANNED_FOLDERS_FILE}.")
        return {}
    with open(SCANNED_FOLDERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_logs():
    scanned_folders = load_scanned_folders()
    if not scanned_folders:
        return

    # Keep track of the current JSON block being parsed
    current_json_block = []
    in_json_block = False

    log_files = glob.glob(os.path.join(LOG_DIR, "*.log"))
    if not log_files:
        logging.warning("No .log files found in the Logs directory.")
        return

    processed_count = 0

    processed_folders = set()

    for log_file in log_files:
        logging.info(f"Parsing log file: {log_file}")
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line_stripped = line.strip()

                if "replay media event: {" in line:
                    in_json_block = True
                    # Extract the JSON part starting from '{'
                    json_start = line[line.find('{'):]
                    current_json_block = [json_start.strip()]
                    brace_count = json_start.count('{') - json_start.count('}')
                    continue
                
                if in_json_block:
                    current_json_block.append(line_stripped)
                    brace_count += line_stripped.count('{') - line_stripped.count('}')
                    
                    if brace_count == 0:
                        in_json_block = False
                        # Parse the collected JSON block
                        json_str = "\n".join(current_json_block)
                        try:
                            event_data = json.loads(json_str)
                            folder_name = process_event(event_data, scanned_folders)
                            if folder_name:
                                processed_folders.add(folder_name)
                            processed_count += 1
                        except json.JSONDecodeError as e:
                            logging.error(f"Failed to decode JSON block: {e}\n{json_str}")
                        current_json_block = []

    # Update scanned_folders map and save it
    if processed_folders:
        for folder in processed_folders:
            scanned_folders[folder] = True
            
        try:
            with open(SCANNED_FOLDERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(scanned_folders, f, indent=4)
            logging.info(f"Updated {SCANNED_FOLDERS_FILE} for {len(processed_folders)} folders.")
        except Exception as e:
            logging.error(f"Failed to update {SCANNED_FOLDERS_FILE}: {e}")

    logging.info(f"Finished parsing logs. Processed {processed_count} highlight events.")

def process_event(event_data, scanned_folders):
    media_path = event_data.get("media_path")
    if not media_path:
        return None

    path_parts = media_path.replace('\\', '/').split('/')
    if len(path_parts) < 2:
        return None
    
    file_name = path_parts[-1]
    folder_name = path_parts[-2]

    # Check against scanned_folders.json
    if folder_name not in scanned_folders:
        return None
    
    if scanned_folders[folder_name] is True:
        return None
    
    if not os.path.exists(media_path):
        logging.warning(f"Video file does not exist: {media_path}")
        return None

    base_name = os.path.splitext(file_name)[0]
    json_path = os.path.join(os.path.dirname(media_path), f"{base_name}.json")
    
    # Calculate kills from event data log
    # event_data["events"] contains a list, count occurrences of "kill"
    raw_events = event_data.get("raw_events", [])
    kills = len([event for event in raw_events if event.get("type") == "kill"])

    # Format the data according to the target output schema specified
    formatted_data = {
        "clip": file_name,
        "match_id": event_data.get("match_id", "Unknown"),
        "map": "Unknown",
        "agent": "Unknown",
        "kills": kills,
        "round": -1,
        "round_details": {}
    }

    # Save the formatted JSON data
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(formatted_data, f, indent=4)
        logging.info(f"Created standard JSON metadata: {json_path}")
        return folder_name
    except Exception as e:
        logging.error(f"Failed to write JSON {json_path}: {e}")
        return None

if __name__ == "__main__":
    parse_logs()
