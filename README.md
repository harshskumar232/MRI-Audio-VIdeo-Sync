================================================================================
MRI SYNC ANALYZER - HOW TO RUN
================================================================================

STEP 1: Install Dependencies
-----------------------------

Open Terminal/Command Prompt and run:

```
pip install librosa opencv-python scipy pandas openpyxl
```

On Mac, use:
```
pip3 install librosa opencv-python scipy pandas openpyxl
```


STEP 2: Install ffmpeg
----------------------

Mac:
```
brew install ffmpeg
```

Windows:
Download from https://ffmpeg.org/download.html

Linux:
```
sudo apt-get install ffmpeg
```


STEP 3: Update Script Paths
----------------------------

Open mri_sync_analyzer_final.py in text editor.

Find the main() function at the end and update:

```python
DATASET_PATH = "/path/to/your/dataset_2drt_video_only"
OUTPUT_DIR = "/path/to/your/output_folder"
```

Examples:

Windows:
```python
DATASET_PATH = "C:\\Users\\YourName\\Desktop\\dataset_2drt_video_only"
OUTPUT_DIR = "C:\\Users\\YourName\\Desktop\\Sync_Analysis"
```

Mac:
```python
DATASET_PATH = "/Users/YourName/Desktop/dataset_2drt_video_only"
OUTPUT_DIR = "/Users/YourName/Desktop/Sync_Analysis"
```

SAVE the file.


STEP 4: Run the Script
----------------------

Terminal/Command Prompt in your project folder:

```
python3 mri_sync_analyzer_final.py
```

Wait 2-4 hours (depends on ~2000 videos).

Progress shows in terminal:
```
[  100/2371]  4.2% | sub001_2drt_01_vcv1_r1_video.mp4 | ETA: 12000s
```


STEP 5: Check Results
---------------------

Open the Excel file:
```
OUTPUT_DIR/MRI_Sync_Analysis_V2.xlsx
```

Contains:
- SUMMARY: Overall stats (clean vs issues)
- 3_DURATION_MISMATCH: Videos with length mismatch
- 5_VARIABLE_DRIFT: Videos with inconsistent audio
- 7_OUTOFSYNC_ENDS: Videos with misaligned ends


================================================================================
THAT'S IT!
================================================================================

Just 2 things:
1. Install libraries (1x, takes 2 min)
2. Update paths in script
3. Run it
4. Check Excel

Questions? Read the SYNC_DETECTION_SUMMARY.txt for what each issue means.
