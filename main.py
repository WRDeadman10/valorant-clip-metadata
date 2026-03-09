import argparse
import sys
import json
from pathlib import Path
from tqdm import tqdm

from config import config
from clip.clip_scanner import scan_clips_directory
from match.match_fetcher import MatchFetcher
from match.match_parser import MatchParser
from output.metadata_writer import write_metadata, write_consolidated_metadata

def load_cached_args():
    cache_file = Path(config.CACHE_DIR) / "cli_args.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cached_args(args_dict):
    cache_file = Path(config.CACHE_DIR) / "cli_args.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(args_dict, f, indent=4)

def parse_args():
    cached = load_cached_args()
    
    parser = argparse.ArgumentParser(description="Attach Valorant match metadata to gameplay clips recorded by Tracker Network.")
    parser.add_argument("--clips", help=f"Directory containing the video clips (default: {cached.get('clips', 'None')})")
    parser.add_argument("--player", help=f"Player ID in the format PlayerName#TAG (default: {cached.get('player', 'None')})")
    parser.add_argument("--region", help=f"Valorant region e.g. ap, na, eu, kr (default: {cached.get('region', 'None')})")
    parser.add_argument("--api", choices=["henrik", "riot"], help=f"API to use (default: {cached.get('api', 'henrik')})")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh match cache by redownloading")
    parser.add_argument("--debug-match", action="store_true", help="Save the full raw API match JSON alongside the clip")
    args = parser.parse_args()
    
    # Merge CLI args with cached args
    final_args = {
        "clips": args.clips or cached.get('clips'),
        "player": args.player or cached.get('player'),
        "region": args.region or cached.get('region'),
        "api": args.api or cached.get('api', 'henrik'),
        "force_refresh": args.force_refresh,
        "debug_match": args.debug_match
    }
    
    # Validate required arguments
    missing = []
    if not final_args["clips"]: missing.append("--clips")
    if not final_args["player"]: missing.append("--player")
    if not final_args["region"]: missing.append("--region")
    
    if missing:
        parser.error(f"Missing required arguments (not provided and not cached): {', '.join(missing)}")
        
    # Save the successful args for next time
    save_args = {k: v for k, v in final_args.items() if k not in ["force_refresh", "debug_match"]}
    save_cached_args(save_args)
    
    # Convert back to namespace for main function compatibility
    return argparse.Namespace(**final_args)

def main():
    args = parse_args()
    
    if "#" not in args.player:
        print("Error: Player name must be in the format PlayerName#TAG (e.g. Player#001)")
        sys.exit(1)
        
    name, tag = args.player.split("#", 1)
    region = args.region.lower()
    clips_dir = args.clips
    
    # Override config default API if specified via CLI
    if args.api:
        config.DEFAULT_API = args.api
        
    print(f"Starting Valorant Clip Metadata Extractor")
    print(f"Targeting: {name}#{tag} in region {region}")
    print(f"Scanning directory: {clips_dir}")
    print("-" * 40)
    
    # 1. Scan for clips
    try:
        clips = scan_clips_directory(clips_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
        
    if not clips:
        print("No supported clips found in the given directory.")
        sys.exit(0)
        
    print(f"Found {len(clips)} supported video clip(s).")
    
    # 2. Fetch recent matches (cached by default locally)
    # Assume 20 covers standard play sessions well
    fetcher = MatchFetcher(api_type=args.api)
    print("Fetching player match history...")
    try:
        matches = fetcher.fetch_matches(region, name, tag, force_refresh=args.force_refresh, size=20)
    except Exception as e:
        print(f"Error fetching matches: {e}")
        sys.exit(1)
        
    print(f"Successfully loaded {len(matches)} recent matches from {fetcher.client.__class__.__name__}.")
    
    # 3. Parse and map each clip to a match
    parser = MatchParser(api_type=args.api)
    processed_count = 0
    consolidated_data = []
    
    print("-" * 40)
    print("Processing clips...")
    
    # Tqdm progress bar for processing visual feedback
    for clip in tqdm(clips, desc="Mapping Clips", unit="clip"):
        match_info = parser.find_match_for_clip(clip.timestamp, matches, name, tag)
        
        if match_info:
            # 4. Write metadata JSON alongside the clip and update counter
            # If debug_match is given, pass the raw match payload as well
            raw_match = match_info.get("_raw_match") if args.debug_match else None
            write_metadata(clip.file_path, match_info, consolidate_list=consolidated_data, debug_match=raw_match)
            processed_count += 1
        else:
            tqdm.write(f"Warning: No match found for clip {clip.filename} around {clip.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # 5. Write consolidated metadata list
    if consolidated_data:
        write_consolidated_metadata(clips_dir, consolidated_data)
        print(f"Saved consolidated metadata for {len(consolidated_data)} clips to {Path(clips_dir) / 'consolidated_metadata.json'}")

    print("-" * 40)
    print(f"Complete! Successfully attached metadata for {processed_count}/{len(clips)} clips.")

if __name__ == "__main__":
    main()
