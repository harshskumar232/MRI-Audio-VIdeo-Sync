================================================================================
MRI AUDIO-VIDEO SYNC ANALYZER - README
How to Run on Your PC
================================================================================

QUICK START (5 minutes)
======================

1. Download the code file: mri_sync_analyzer_final.py
2. Put it in your project folder
3. Open Terminal/Command Prompt
4. Run: python3 mri_sync_analyzer_final.py
5. Wait 2-4 hours for analysis
6. Check the Excel report in output folder


================================================================================
DETAILED SETUP INSTRUCTIONS
================================================================================

STEP 1: Install Python (if not already installed)
------------------------------------------------------

Windows:
  - Go to: https://www.python.org/downloads/
  - Download Python 3.9 or newer
  - During installation: CHECK "Add Python to PATH"
  - Click Install

Mac:
  - Python usually comes pre-installed
  - Or install via Homebrew:
    ```
    brew install python3
    ```

Linux:
  - Already installed, just use: python3


STEP 2: Install Required Libraries
------------------------------------------------------

Open Terminal/Command Prompt and run:

```
pip install librosa opencv-python scipy pandas openpyxl
```

Wait for installation to complete (2-3 minutes).

On Mac, you might need:
```
pip3 install librosa opencv-python scipy pandas openpyxl
```


STEP 3: Install ffmpeg (for audio extraction)
------------------------------------------------------

Windows:
  - Download from: https://ffmpeg.org/download.html
  - Extract to C:\ffmpeg
  - Add to system PATH (or just extract next to script)

Mac:
  - Open Terminal and run:
    ```
    brew install ffmpeg
    ```

Linux:
  - Ubuntu/Debian:
    ```
    sudo apt-get install ffmpeg
    ```


STEP 4: Prepare Your Data Folder
------------------------------------------------------

Organize your videos in this structure:

```
your_project_folder/
├── dataset_videos/
│   ├── sub001/
│   │   ├── 2drt/
│   │   │   ├── video/
│   │   │   │   ├── sub001_2drt_01_*.mp4
│   │   │   │   ├── sub001_2drt_02_*.mp4
│   │   │   │   └── ...more videos...
│   ├── sub002/
│   │   ├── 2drt/
│   │   │   ├── video/
│   │   │   │   └── ...videos...
│   └── ... (sub003 to sub075)
├── mri_sync_analyzer_final.py  ← Your analyzer script
└── Sync_Analysis_Results/      ← Will be created automatically
```

The code uses `rglob("*.mp4")` to find ALL .mp4 files recursively.


STEP 5: Update the Script Paths (IMPORTANT!)
------------------------------------------------------

Open mri_sync_analyzer_final.py in a text editor.

Find the main() function at the bottom:

```python
def main():
    DATASET_PATH = "/Users/harshkumar/Desktop/MRI Project/dataset_2drt_video_only"
    OUTPUT_DIR = "/Users/harshkumar/Desktop/MRI Project/Sync_Analysis_V2"
```

Change these to YOUR paths:

Windows example:
```python
DATASET_PATH = "C:\\Users\\YourName\\Desktop\\MRI_Data\\videos"
OUTPUT_DIR = "C:\\Users\\YourName\\Desktop\\MRI_Data\\Results"
```

Mac example:
```python
DATASET_PATH = "/Users/YourName/Desktop/MRI_Data/videos"
OUTPUT_DIR = "/Users/YourName/Desktop/MRI_Data/Results"
```

Linux example:
```python
DATASET_PATH = "/home/YourName/mri_data/videos"
OUTPUT_DIR = "/home/YourName/mri_data/results"
```

SAVE the file after changes!


STEP 6: Run the Analyzer
------------------------------------------------------

Open Terminal/Command Prompt in your project folder.

Windows:
  ```
  python mri_sync_analyzer_final.py
  ```

Mac/Linux:
  ```
  python3 mri_sync_analyzer_final.py
  ```

You should see:
```
================================================================================
🔍 MRI SYNC ANALYZER V2 (REALISTIC THRESHOLDS)
Only flags PERCEPTIBLE issues (>50ms desync, >2% duration diff)
================================================================================
Found XXXX video files...

[   1/XXXX]   0.0% | filename.mp4 | ETA: 14400s
[   2/XXXX]   0.1% | filename.mp4 | ETA: 14300s
...
```

Let it run! ☕ (2-4 hours for 2000+ videos)


STEP 7: Check Results
------------------------------------------------------

After completion, you'll see:

```
✅ Analysis complete! XXXX files in 9876.4s (164.6min)
================================================================================

ISSUE SUMMARY
================================================================================

Total: XXXX | Clean: XXXX | Issues: XXXX

  3_DURATION_MISMATCH    :  XXX
  5_VARIABLE_DRIFT       :  XXX
  7_OUTOFSYNC_ENDS       :  XXX
```

Open the Excel file:
  OUTPUT_DIR/MRI_Sync_Analysis_V2.xlsx

It contains:
  - SUMMARY sheet (overall stats)
  - One sheet per issue type
  - Each sheet lists problematic files


================================================================================
TROUBLESHOOTING
================================================================================

ERROR: "ffprobe not found"
  → ffmpeg not installed
  → Install it: brew install ffmpeg (Mac) or download from ffmpeg.org

ERROR: "ModuleNotFoundError: librosa"
  → Missing library
  → Run: pip install librosa

ERROR: "No such file or directory"
  → Wrong path in script
  → Check DATASET_PATH and OUTPUT_DIR paths

ERROR: "No video files found"
  → Videos not in expected structure
  → Check folder hierarchy matches example above

ERROR: Script runs but takes forever
  → Normal! 2000+ videos = 2-4 hours
  → Leave it running, don't close terminal


================================================================================
WHAT THE SCRIPT DOES (Step by Step)
================================================================================

1. SCAN:    Finds all .mp4 files recursively
2. EXTRACT: Gets video duration, FPS, frame count
3. EXTRACT: Gets audio duration, sample rate
4. ANALYZE: Runs 8 checks on each video:
            - Missing audio?
            - Silent audio?
            - Duration mismatch?
            - Constant offset?
            - Variable drift?
            - Audio corruption?
            - Out-of-sync ends?
            - Low quality?
5. RECORD:  Saves results for each video
6. REPORT:  Creates Excel file with results
7. PRINT:   Shows summary in terminal


================================================================================
UNDERSTANDING THE RESULTS
================================================================================

Each video is analyzed and flagged as:

✅ CLEAN - No issues found (89.1% of videos typically)

❌ FLAGGED - One or more issues found:

  3_DURATION_MISMATCH
    → Audio and video length differ by >2%
    → Example: Video 25.99s, Audio 26.55s
    → Fix: Re-encode to match lengths

  5_VARIABLE_DRIFT
    → Audio quality changes drastically across video
    → Suggests: Frame drops in video but not audio
    → Fix: Check for frame drop issues

  7_OUTOFSYNC_ENDS
    → Video and audio don't end at same time
    → Example: Video ends at 55s, audio at 55.3s
    → Fix: Trim or re-align ends

  4_CONSTANT_OFFSET
    → Audio delayed/ahead throughout video
    → Example: Audio always 150ms late
    → Fix: Shift audio to align

  6_AUDIO_CORRUPTION
    → Audio is distorted or clipped
    → Fix: Re-record or use lower gain

  8_LOW_AUDIO_QUALITY
    → Audio over-compressed
    → Fix: Use better encoding


================================================================================
CUSTOMIZING THE SCRIPT
================================================================================

To change detection thresholds, edit these lines in the class:

PERCEPTIBLE_DESYNC_MS = 50        # Only flag if >50ms offset
SERIOUS_DESYNC_MS = 150           # Severe desync threshold
ACCEPTABLE_DURATION_DIFF_PCT = 2.0  # Only flag if >2% mismatch

Example: To only flag duration mismatches >3%:
```python
ACCEPTABLE_DURATION_DIFF_PCT = 3.0
```

Example: To be more sensitive to offsets (flag >30ms):
```python
PERCEPTIBLE_DESYNC_MS = 30
```

Save after changes and run again!


================================================================================
SHARING RESULTS
================================================================================

To share results with others:

1. Give them the analyzer script: mri_sync_analyzer_final.py
2. They update DATASET_PATH and OUTPUT_DIR with their own paths
3. They run: python3 mri_sync_analyzer_final.py
4. They get their own Excel report

The script works on ANY dataset with this structure:
```
dataset/
├── sub001/2drt/video/*.mp4
├── sub002/2drt/video/*.mp4
└── ... etc
```


================================================================================
REQUIREMENTS SUMMARY
================================================================================

System:
  - Windows 10+, Mac OS 10.14+, or Linux
  - 4GB RAM minimum
  - 5GB free disk space (for temp files)
  - Python 3.8+

Software:
  - Python 3.8 or newer
  - ffmpeg
  - librosa
  - opencv-python
  - scipy
  - pandas
  - openpyxl

Time:
  - 2000 videos = 2-4 hours
  - ~5-7 seconds per video
  - Depends on video length and CPU speed


================================================================================
COMMAND CHEAT SHEET
================================================================================

Install libraries:
  pip install librosa opencv-python scipy pandas openpyxl

Install ffmpeg:
  Mac:   brew install ffmpeg
  Windows: Download from ffmpeg.org
  Linux:   sudo apt-get install ffmpeg

Run analyzer:
  python3 mri_sync_analyzer_final.py

Check Python version:
  python3 --version

List installed packages:
  pip list


================================================================================
CONTACT & QUESTIONS
================================================================================

If script doesn't work:
1. Check error message carefully
2. Verify paths are correct (forward slashes on Mac/Linux, backslashes on Windows)
3. Verify all libraries installed: pip list
4. Verify ffmpeg installed: ffmpeg -version

For issues:
- Check that all video files are .mp4 format
- Check folder structure matches expected hierarchy
- Try running on a small subset first (10 videos in one folder)


================================================================================
VERSION INFO
================================================================================

Script Version: MRI_Sync_Analyzer_V2
Release Date: 2026-09-24
Python: 3.8+
Libraries: librosa, opencv, scipy, pandas, openpyxl

What's New:
  - Only flags PERCEPTIBLE issues (>50ms)
  - Cross-correlation for offset detection
  - 89.1% clean videos (low false positives)
  - Excel report with per-issue sheets


================================================================================
END OF README
================================================================================
