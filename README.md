# Valorant Clip Metadata Extractor

A powerful Python CLI tool designed to automatically enrich raw Valorant gameplay clips with their exact corresponding in-game match metadata.

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [How it Works](#how-it-works)
- [Setup & Requirements](#setup--requirements)
- [Usage (Single Folder)](#usage-single-folder)
- [Usage (Batch Processing)](#usage-batch-processing)
- [API Limitations & Historical Clips](#api-limitations--historical-clips)

## Overview
When recording Valorant clips using software like Tracker Network, the raw video files are saved with timestamps but lack the actual in-game context (Match ID, exact round played, kills achieved in that round, weapon used, etc.). 

This tool scans your clip directories, precisely timestamps the video file, communicates with Valorant APIs in the background to find that exact match, and automatically generates detailed JSON metadata dictionaries specifically pinpointing the player's performance in the exact round the clip occurred in.

## Key Features
1. **Pinpoint Round Mapping**: Calculates exactly which round your 30-second clip occurred in by matching your local video creation time against the official Riot match timeline API.
2. **True Kill Statistics**: Extracts *only* the kills the player achieved in the specific round the clip was recorded in (omitting kills from earlier/later rounds).
3. **Advanced Damage Breakdown**: Provides a `round_details` dictionary mapping the exact victims, weapons used, and damage dealt for every kill in the clip.
4. **Interchangeable APIs**: Full support for both the unofficial **HenrikDev V3** API (default/free) and the official **Riot API**.
5. **Smart Rate-Limit Evasion**: Uses robust file-based caching with an intelligent 1-hour expiration buffer, guaranteeing you won't get banned for API spam.
6. **Background Batching**: Includes a smart directory crawler (`batch_runner.py`) that safely processes hundreds of legacy folders while adhering strictly to API throttling rules (30 requests/min).
7. **Auto-Resume Skip Logic**: The batch processor stores results in `scanned_folders.json`. If execution is stopped, it instantly resumes exactly where it left off, bypassing previously verified folders natively.

## How it Works
1. Scans a Tracker Network video filename (e.g., `VALORANT 03-08-2026 2-46-25-817.mp4`) assuming local Indian Standard Time (IST).
2. Converts the time to UTC.
3. Downloads the player's recent matches.
4. Finds the match where the `game_start` + `game_length` precisely overlaps with the video's UTC timestamp.
5. Scrubs the match `kill_events` timeline to locate kills matching the player's PUUID occurring before the clip ended.
6. Spits out `clip_name.json` next to the video file, plus a `consolidated_metadata.json` for the entire batch.

## Setup & Requirements

**Requirements:**
- Python 3.10+
- `requests`
- `python-dateutil`
- `tqdm`
- `pydantic`

**Installation:**
```bash
pip install requests python-dateutil tqdm pydantic
```

**API Configuration (`config.py`)**:
The script defaults to using the HenrikDev API. Place your API keys into `config.py` appropriately.

## Usage (Single Folder)
If you just played a game and want to parse the immediate folder:

```bash
python main.py --clips "E:\Path\To\VALORANT_FOLDER" --player "YourName#Tag" --region ap
```

**Flags:**
- `--api`: Switch between `henrik` (default) and `riot`
- `--force-refresh`: Ignore the local 1-hour `.cache` and force a new API pull
- `--debug-match`: Save the massive 2MB raw match JSON payload for advanced debugging

*Note: Your CLI arguments are cached seamlessly. For subsequent runs on the same player, simply running `python main.py --clips "..."` is sufficient.*

## Usage (Batch Processing)
If you have a massive root directory containing hundreds of Tracker `.mp4` subfolders, use the batch processing script:

```bash
python batch_runner.py
```
*You must hardcode your Root Directory and Player Profile at the top of `batch_runner.py` before executing.*

The batch processor will queue every subfolder chronologically, trigger 1 API search per folder, wait 2 seconds, and proceed to the next—ensuring compliance with the strict 30 hit/minute rate limit. Fully crash safe.

## API Limitations & Historical Clips
**WARNING:** In June 2023, Riot Games heavily restricted their official API. 

The API **only returns the last 10 to 20 recent matches** for any player. It is fundamentally impossible to query deep historic matches (e.g., retrieving January matches in March). If you run `batch_runner.py` on clips older than your last 20 games, the script will successfully parse your folder but warn that "No match was found". The Riot servers actively delete deep match history query availability.

Ensure you process your clips sequentially between gaming sessions for a 100% success rate!
