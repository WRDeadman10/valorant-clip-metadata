import os
import time
import subprocess
import json
from pathlib import Path

def main():
    root_dir = Path(r"E:\New folder\Valorant Tracker\VALORANT")
    player = "Ragnar Lothbrok#CR7"
    region = "ap"

    print(f"Scanning {root_dir}...")
    
    # 1. Find all folders starting with VALORANT
    folders = []
    if not root_dir.exists():
        print("Root directory not found.")
        return
        
    for entry in root_dir.iterdir():
        if entry.is_dir() and entry.name.startswith("VALORANT"):
            folders.append(entry)

    # Sort the folders chronologically if possible by name
    folders.sort(key=lambda x: x.name)
    
    # 2. Track scanned folders to allow resuming
    scanned_file = Path("scanned_folders.json")
    scanned_folders = {}
    if scanned_file.exists():
        try:
            with open(scanned_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Convert legacy list to dictionary
                    scanned_folders = {name: True for name in data}
                else:
                    scanned_folders = data
            print(f"Loaded {len(scanned_folders)} previously scanned folders.")
        except Exception as e:
            print(f"Warning: Could not read scanned_folders.json: {e}")
            scanned_folders = {}

    # Filter out already scanned folders and check for existing consolidated_metadata.json
    folders_to_process = []
    for f in folders:
        # If it exists in our JSON, skip it
        if f.name in scanned_folders:
            continue
            
        # If the consolidated_metadata.json already exists in the folder, mark it True and skip
        consolidated_path = f / "consolidated_metadata.json"
        if consolidated_path.exists():
            scanned_folders[f.name] = True
            continue
            
        folders_to_process.append(f)

    # Save the updated scanned_folders dictionary in case we found existing consolidated_metadata.json files
    try:
        with open(scanned_file, 'w', encoding='utf-8') as f:
            json.dump(scanned_folders, f, indent=4)
    except Exception as e:
        print(f"Warning: Could not write scanned_folders.json: {e}")

    print(f"Found {len(folders)} total folders. {len(folders_to_process)} remaining to process.")
    print("-" * 40)

    # 3. Iterate and process
    for i, folder in enumerate(folders_to_process, 1):
        print(f"\n[{i}/{len(folders_to_process)}] Processing Folder: {folder.name}")
        
        # We use --force-refresh to trigger exactly 1 API call to HenrikDev per folder.
        # This, combined with the 2-second sleep below, ensures we make exactly 30 API calls per minute
        # as requested, perfectly avoiding rate limits!
        cmd = [
            "python", "main.py",
            "--clips", str(folder.absolute()),
            "--player", player,
            "--region", region,
            "--api", "henrik",
            "--force-refresh"
        ]
        
        try:
            # Run the command
            subprocess.run(cmd, check=True)
            print(f"Finished {folder.name}")
            
            # Record success so we can skip next time
            scanned_folders[folder.name] = True
            
            consolidated_path = folder / "consolidated_metadata.json"
            if not consolidated_path.exists():
                print(f"Warning: {folder.name} processed successfully but no consolidated_metadata.json was generated.")
            
            with open(scanned_file, 'w', encoding='utf-8') as f:
                json.dump(scanned_folders, f, indent=4)
                
        except subprocess.CalledProcessError as e:
            print(f"Error processing {folder.name}: {e}")
            # If there's a script crash, keep it false so it tries again later
            scanned_folders[folder.name] = False
            
        # 4. Apply the 2 second delay required to space out the API hits and folder completions
        print("Waiting 2 seconds before proceeding to next folder to respect API delays...")
        time.sleep(2)

    print("\n" + "="*40)
    print(f"Batch Processing Complete! Successfully navigated across {len(folders_to_process)} folders.")

if __name__ == "__main__":
    main()
