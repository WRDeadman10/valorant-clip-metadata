import json
from pathlib import Path

def write_metadata(clip_path: str, metadata: dict, consolidate_list: list = None, debug_match: dict = None) -> str:
    """
    Writes the extracted match metadata to a JSON file alongside the clip.
    If consolidate_list is provided, appends the metadata to it.
    If debug_match is provided, writes the raw match API payload to a separate file.
    Returns the absolute path to the saved JSON file.
    """

    path = Path(clip_path)
    # The output filename will be the original clip name with .json
    output_filename = f"{path.stem}.json"
    output_path = path.parent / output_filename
    
    # Required keys: clip, match_id, map, agent, kills, round
    output_data = {
        "clip": path.name,
        "match_id": metadata.get("match_id", "Unknown"),
        "map": metadata.get("map", "Unknown"),
        "agent": metadata.get("agent", "Unknown"),
        "kills": metadata.get("kills", 0),
        "round": metadata.get("round", -1),
        "round_details": metadata.get("round_details", {})
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4)
        
    if consolidate_list is not None:
        consolidate_list.append(output_data)
        
    if debug_match is not None:
        debug_filename = f"{path.stem}_debug_match.json"
        debug_path = path.parent / debug_filename
        with open(debug_path, 'w', encoding='utf-8') as f:
            json.dump(debug_match, f, indent=4)
            
    return str(output_path.absolute())

def write_consolidated_metadata(directory_path: str, consolidated_data: list) -> str:
    """
    Writes all extracted metadata from the batch into a single consolidated JSON file
    in the clips directory.
    """
    output_path = Path(directory_path) / "consolidated_metadata.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(consolidated_data, f, indent=4)
        
    return str(output_path.absolute())
