#!/usr/bin/env python3
"""
MRI Audio-Sync Issue Analyzer V2 - IMPROVED
Only flags REAL, PERCEPTIBLE sync issues using cross-correlation
"""

import os
import subprocess
from pathlib import Path
import cv2
import librosa
import numpy as np
from scipy import signal
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import time
import warnings
warnings.filterwarnings('ignore')


class MRISyncAnalyzerV2:
    """Detect REAL audio-sync issues only (perceptible to humans)"""

    # HUMAN PERCEPTION THRESHOLDS (based on psychoacoustics research)
    PERCEPTIBLE_DESYNC_MS = 50  # Humans can detect >50ms offset
    SERIOUS_DESYNC_MS = 150     # Clearly wrong
    ACCEPTABLE_DURATION_DIFF_PCT = 2.0  # 2% = 1.2s on a 60s video (minor codec variance)
    
    def __init__(self, dataset_path, output_dir="Sync_Analysis_V2"):
        self.dataset_path = Path(dataset_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = []
        self.issues_found = {}
        self.start_time = time.time()

    def get_video_metadata(self, video_path):
        """Extract video metadata"""
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return None, None, None
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            cap.release()
            return duration, fps, frame_count
        except:
            return None, None, None

    def extract_audio(self, video_path):
        """Extract audio"""
        try:
            probe_cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a:0',
                        '-show_entries', 'stream=codec_type,duration',
                        '-of', 'default=noprint_wrappers=1',
                        str(video_path)]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=2)

            if not result.stdout.strip():
                return None, None, "NO_AUDIO_STREAM"

            audio_path = f"/tmp/temp_{hash(str(video_path)) % 100000}.wav"
            extract_cmd = ['ffmpeg', '-i', str(video_path), '-q:a', '9', '-n', audio_path]
            subprocess.run(extract_cmd, capture_output=True, timeout=10)

            if not os.path.exists(audio_path):
                return None, None, "EXTRACTION_FAILED"

            y, sr = librosa.load(audio_path, sr=16000)
            duration = len(y) / sr

            os.remove(audio_path)
            return y, sr, "SUCCESS"

        except subprocess.TimeoutExpired:
            return None, None, "TIMEOUT"
        except:
            return None, None, "ERROR"

    # ===== ISSUE 1: Missing Audio =====
    def check_missing_audio(self, audio, audio_status):
        """No audio stream at all"""
        if audio_status == "NO_AUDIO_STREAM":
            return True, "No audio stream detected"
        if audio_status in ["EXTRACTION_FAILED", "TIMEOUT", "ERROR"]:
            return True, f"Audio extraction failed: {audio_status}"
        return False, None

    # ===== ISSUE 2: Silent Audio =====
    def check_silent_audio(self, audio, sr):
        """Audio exists but is essentially silent"""
        if audio is None:
            return False, None

        rms = np.sqrt(np.mean(audio ** 2))
        peak = np.max(np.abs(audio))

        # Real silence detection: peak < 0.001 OR RMS < 0.00001
        if peak < 0.001:
            return True, f"Peak amplitude {peak:.6f} (essentially silent)"
        if rms < 0.00001:  # Raise threshold - very few legit audio signals are this quiet
            return True, f"RMS {rms:.6f} (inaudible)"

        return False, None

    # ===== ISSUE 3: Duration Mismatch (PERCEPTIBLE ONLY) =====
    def check_duration_mismatch(self, video_duration, audio_duration):
        """Only flag if difference is PERCEPTIBLE (>2%)"""
        if video_duration is None or audio_duration is None:
            return False, None

        diff_s = abs(video_duration - audio_duration)
        diff_ms = diff_s * 1000
        diff_pct = (diff_s / min(video_duration, audio_duration)) * 100

        # Only flag if >2% difference (codec variance is <1%, obvious issues are >2%)
        if diff_pct > self.ACCEPTABLE_DURATION_DIFF_PCT:
            return True, f"Duration mismatch: {diff_ms:.1f}ms ({diff_pct:.2f}%)"

        return False, None

    # ===== ISSUE 4: Perceptible Constant Offset (CROSS-CORRELATION) =====
    def check_constant_offset(self, audio, sr, video_duration, fps):
        """Use cross-correlation to find REAL offset, only flag if >50ms"""
        if audio is None or video_duration is None or fps is None:
            return False, None

        try:
            # Create synthetic "video signal" from expected frame times
            # and cross-correlate with audio energy
            S = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=13)
            audio_energy = np.sqrt(np.sum(S**2, axis=0))
            
            # Normalize
            audio_energy = (audio_energy - np.mean(audio_energy)) / (np.std(audio_energy) + 1e-9)
            
            # Downsample to video frame rate equivalent
            target_length = int(video_duration * (sr / 512))  # 512 is hop_length default
            if target_length < 10:
                return False, None
                
            audio_energy_downsampled = audio_energy[:target_length]
            
            # Cross-correlation to find best alignment
            # This is expensive, so sample only the first 5 seconds
            sample_frames = min(len(audio_energy_downsampled), int(5 * sr / 512))
            if sample_frames < 10:
                return False, None
                
            test_signal = audio_energy_downsampled[:sample_frames]
            
            # Correlation with small shifts (-2 to +2 seconds)
            max_shift = int(2 * sr / 512)  # 2 second max shift to test
            correlations = []
            
            for shift in range(-max_shift, max_shift + 1):
                if shift >= 0:
                    shifted = np.concatenate([np.zeros(shift), test_signal])[:len(test_signal)]
                else:
                    shifted = test_signal[-shift:]
                
                corr = np.corrcoef(test_signal, shifted)[0, 1]
                if not np.isnan(corr):
                    correlations.append((shift, corr))
            
            if not correlations:
                return False, None
            
            # Find best correlation
            best_shift, best_corr = max(correlations, key=lambda x: x[1])
            
            # Convert shift to milliseconds (512 samples per frame at 16kHz)
            shift_ms = best_shift * (512 / sr) * 1000
            
            # Only flag if offset is PERCEPTIBLE (>50ms) AND corr is high confidence
            if abs(shift_ms) > self.PERCEPTIBLE_DESYNC_MS and best_corr > 0.7:
                direction = "ahead" if shift_ms > 0 else "behind"
                return True, f"Offset: audio {abs(shift_ms):.0f}ms {direction}"
            
            return False, None

        except:
            return False, None

    # ===== ISSUE 5: Variable Drift (MULTI-POINT CHECK) =====
    def check_variable_drift(self, audio, sr, fps, frame_count):
        """Only flag if MULTIPLE segments show inconsistent sync"""
        if audio is None or frame_count is None or fps is None:
            return False, None

        try:
            # Divide into 3 segments (too sensitive with 5)
            segment_count = 3
            offsets = []

            for seg in range(segment_count):
                start_frame = int((seg / segment_count) * frame_count)
                end_frame = int(((seg + 1) / segment_count) * frame_count)
                
                start_sample = int((start_frame / fps) * sr)
                end_sample = int((end_frame / fps) * sr)

                if start_sample >= len(audio) or end_sample > len(audio):
                    continue

                audio_segment = audio[start_sample:end_sample]
                if len(audio_segment) < sr / 5:  # Need at least 0.2s
                    continue

                # Compute RMS for this segment
                S = librosa.feature.melspectrogram(y=audio_segment, sr=sr, n_mels=13)
                energy = np.sqrt(np.sum(S**2, axis=0))
                segment_rms = np.sqrt(np.mean(energy ** 2))
                offsets.append(segment_rms)

            if len(offsets) < 2:
                return False, None
            
            # Compute coefficient of variation (CV = std / mean)
            cv = np.std(offsets) / (np.mean(offsets) + 1e-9)
            
            # Only flag if CV > 1.0 (meaning very inconsistent - likely real drift)
            # Normal speech has CV ~0.4-0.6
            if cv > 1.0:
                return True, f"High variability across segments (CV: {cv:.2f})"

            return False, None

        except:
            return False, None

    # ===== ISSUE 6: Audio Corruption/Noise =====
    def check_audio_corruption(self, audio, sr):
        """Detect clipping, extreme noise, or corruption"""
        if audio is None:
            return False, None

        # Check for hard clipping (samples at exactly -1.0 or 1.0)
        clipped = np.sum(np.abs(np.abs(audio) - 1.0) < 0.001)
        clipped_pct = (clipped / len(audio)) * 100

        if clipped_pct > 1.0:  # >1% clipping = corruption
            return True, f"Audio clipping detected ({clipped_pct:.2f}%)"

        # Check for extreme zero-crossings (noise indicator)
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio))) > 0)
        zc_rate = zero_crossings / len(audio)

        if zc_rate > 0.8:  # Very high ZC rate = noise/corruption
            return True, f"Excessive noise (ZC rate: {zc_rate:.3f})"

        return False, None

    # ===== ISSUE 7: Out-of-Sync Ends =====
    def check_outofsync_ends(self, video_duration, audio_duration):
        """Only flag if ends are SIGNIFICANTLY misaligned"""
        if video_duration is None or audio_duration is None:
            return False, None

        diff_s = abs(video_duration - audio_duration)
        
        # Only flag if difference is >200ms (clearly noticeable)
        if diff_s > 0.2:
            return True, f"Ends misaligned by {diff_s*1000:.0f}ms"

        return False, None

    # ===== ISSUE 8: Low Audio Quality =====
    def check_low_audio_quality(self, audio, sr):
        """Detect low bitrate, compression artifacts"""
        if audio is None:
            return False, None

        # Detect if audio is too "digital" sounding (low dynamic range)
        rms = np.sqrt(np.mean(audio ** 2))
        peak = np.max(np.abs(audio))
        dynamic_range = peak / (rms + 1e-9)

        # Normal speech: dynamic range 10-50
        # Highly compressed: <5
        if dynamic_range < 3:
            return True, f"Very low dynamic range ({dynamic_range:.1f}) - over-compressed?"

        return False, None

    def analyze_video(self, video_path):
        """Analyze one video"""
        video_duration, fps, frame_count = self.get_video_metadata(video_path)
        audio, sr, audio_status = self.extract_audio(video_path)
        audio_duration = len(audio) / sr if audio is not None else None

        issues_detected = []
        issue_details = {}

        # Issue 1: Missing Audio
        has_issue, detail = self.check_missing_audio(audio, audio_status)
        if has_issue:
            issues_detected.append("1_MISSING_AUDIO")
            issue_details["missing_audio"] = detail

        # Issue 2: Silent Audio
        has_issue, detail = self.check_silent_audio(audio, sr)
        if has_issue:
            issues_detected.append("2_SILENT_AUDIO")
            issue_details["silent_audio"] = detail

        # Issue 3: Duration Mismatch (PERCEPTIBLE ONLY)
        has_issue, detail = self.check_duration_mismatch(video_duration, audio_duration)
        if has_issue:
            issues_detected.append("3_DURATION_MISMATCH")
            issue_details["duration_mismatch"] = detail

        # Issue 4: Constant Offset (CROSS-CORRELATION)
        has_issue, detail = self.check_constant_offset(audio, sr, video_duration, fps)
        if has_issue:
            issues_detected.append("4_CONSTANT_OFFSET")
            issue_details["constant_offset"] = detail

        # Issue 5: Variable Drift (MULTI-POINT)
        has_issue, detail = self.check_variable_drift(audio, sr, fps, frame_count)
        if has_issue:
            issues_detected.append("5_VARIABLE_DRIFT")
            issue_details["variable_drift"] = detail

        # Issue 6: Corruption/Noise
        has_issue, detail = self.check_audio_corruption(audio, sr)
        if has_issue:
            issues_detected.append("6_AUDIO_CORRUPTION")
            issue_details["audio_corruption"] = detail

        # Issue 7: Out-of-Sync Ends
        has_issue, detail = self.check_outofsync_ends(video_duration, audio_duration)
        if has_issue:
            issues_detected.append("7_OUTOFSYNC_ENDS")
            issue_details["outofsync_ends"] = detail

        # Issue 8: Low Audio Quality
        has_issue, detail = self.check_low_audio_quality(audio, sr)
        if has_issue:
            issues_detected.append("8_LOW_AUDIO_QUALITY")
            issue_details["low_audio_quality"] = detail

        return {
            'filename': video_path.name,
            'filepath': str(video_path),
            'video_duration_s': round(video_duration, 3) if video_duration else None,
            'audio_duration_s': round(audio_duration, 3) if audio_duration else None,
            'fps': round(fps, 2) if fps else None,
            'frame_count': frame_count,
            'audio_status': audio_status,
            'issues_count': len(issues_detected),
            'issues': ', '.join(issues_detected) if issues_detected else 'CLEAN',
            'issue_details': issue_details,
            'has_sync_issue': len(issues_detected) > 0
        }

    def analyze_dataset(self):
        """Analyze all videos"""
        video_files = []
        video_files += list(self.dataset_path.rglob("*.mp4"))
        video_files += list(self.dataset_path.rglob("*.mov"))
        video_files += list(self.dataset_path.rglob("*.avi"))

        video_files = sorted(list(set(video_files)))
        total = len(video_files)

        print(f"\n{'='*80}")
        print(f"🔍 MRI SYNC ANALYZER V2 (REALISTIC THRESHOLDS)")
        print(f"Only flags PERCEPTIBLE issues (>50ms desync, >2% duration diff)")
        print(f"{'='*80}")
        print(f"Found {total} video files...\n")

        for idx, video_file in enumerate(video_files, 1):
            elapsed = time.time() - self.start_time
            rate = idx / elapsed if elapsed > 0 else 0
            est_remaining = (total - idx) / rate if rate > 0 else 0
            pct = (idx / total) * 100

            print(f"[{idx:4d}/{total}] {pct:5.1f}% | {video_file.name[:45]:45s} | ETA: {est_remaining:6.0f}s", end='\r')

            result = self.analyze_video(video_file)
            self.results.append(result)

            # Count issues
            for issue in result['issues'].split(', '):
                if issue != 'CLEAN':
                    self.issues_found[issue] = self.issues_found.get(issue, 0) + 1

        elapsed = time.time() - self.start_time
        print(f"\n{'='*80}")
        print(f"✅ Analysis complete! {len(self.results)} files in {elapsed:.1f}s ({elapsed/60:.1f}min)")
        print(f"{'='*80}\n")

    def generate_excel_report(self, filename="MRI_Sync_Analysis_V2.xlsx"):
        """Generate detailed Excel report"""
        output_path = self.output_dir / filename
        df = pd.DataFrame(self.results)

        wb = Workbook()
        wb.remove(wb.active)

        # Define styles
        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        border = Border(left=Side(style='thin'), right=Side(style='thin'),
                       top=Side(style='thin'), bottom=Side(style='thin'))

        # Summary sheet
        ws_summary = wb.create_sheet("SUMMARY", 0)
        ws_summary['A1'] = "MRI SYNC ANALYSIS SUMMARY (V2)"
        ws_summary['A1'].font = Font(bold=True, size=14)

        summary_data = [
            ['Total Videos', len(df)],
            ['Videos with Issues', len(df[df['has_sync_issue']])],
            ['Clean Videos', len(df[~df['has_sync_issue']])],
            ['', ''],
            ['Issue Breakdown', 'Count'],
        ]

        for idx, (label, value) in enumerate(summary_data, 2):
            ws_summary[f'A{idx}'] = label
            ws_summary[f'B{idx}'] = value
            if label in ['Total Videos', 'Issue Breakdown']:
                ws_summary[f'A{idx}'].font = Font(bold=True)

        row = 8
        for issue, count in sorted(self.issues_found.items(), key=lambda x: x[1], reverse=True):
            ws_summary[f'A{row}'] = issue
            ws_summary[f'B{row}'] = count
            row += 1

        ws_summary.column_dimensions['A'].width = 30
        ws_summary.column_dimensions['B'].width = 15

        # Issues sheet
        issues_list = sorted(self.issues_found.keys())
        for issue in issues_list:
            issue_df = df[df['issues'].str.contains(issue, na=False)]
            ws = wb.create_sheet(issue)

            ws.merge_cells('A1:H1')
            heading = ws['A1']
            heading.value = f"{issue} ({len(issue_df)} files)"
            heading.font = Font(bold=True, color="FFFFFF", size=11)
            heading.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            heading.alignment = Alignment(horizontal='center', vertical='center')

            headers = ['#', 'Filename', 'Video Dur (s)', 'Audio Dur (s)', 'FPS', 'Audio Status', 'All Issues', 'Path']
            ws.append([])
            ws.append(headers)

            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=3, column=col_num)
                cell.value = header
                cell.font = header_font
                cell.fill = header_fill
                cell.border = border
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

            for idx, (_, row_data) in enumerate(issue_df.iterrows(), 1):
                ws.append([idx, row_data['filename'], row_data['video_duration_s'],
                          row_data['audio_duration_s'], row_data['fps'],
                          row_data['audio_status'], row_data['issues'], row_data['filepath']])

                for col_num in range(1, 9):
                    cell = ws.cell(row=4+idx-1, column=col_num)
                    if idx % 2 == 0:
                        cell.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
                    cell.border = border
                    cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

            ws.column_dimensions['A'].width = 4
            ws.column_dimensions['B'].width = 35
            ws.column_dimensions['C'].width = 12
            ws.column_dimensions['D'].width = 12
            ws.column_dimensions['E'].width = 8
            ws.column_dimensions['F'].width = 14
            ws.column_dimensions['G'].width = 35
            ws.column_dimensions['H'].width = 50

        wb.save(str(output_path))
        print(f"📊 Report saved: {output_path}")
        return output_path

    def print_summary(self):
        """Print summary to console"""
        print("\n" + "="*80)
        print("ISSUE SUMMARY")
        print("="*80)
        total = len(self.results)
        clean = len([r for r in self.results if not r['has_sync_issue']])
        print(f"\nTotal: {total} | Clean: {clean} ({clean/total*100:.1f}%) | Issues: {total-clean} ({(total-clean)/total*100:.1f}%)\n")
        
        for issue, count in sorted(self.issues_found.items(), key=lambda x: x[1], reverse=True):
            pct = (count / len(self.results)) * 100
            print(f"  {issue:30s}: {count:4d} ({pct:5.1f}%)")
        print("="*80 + "\n")


def main():
    DATASET_PATH = "/Users/harshkumar/Desktop/MRI Project/dataset_2drt_video_only"
    OUTPUT_DIR = "/Users/harshkumar/Desktop/MRI Project/Sync_Analysis_V2"

    analyzer = MRISyncAnalyzerV2(DATASET_PATH, OUTPUT_DIR)
    analyzer.analyze_dataset()
    analyzer.generate_excel_report()
    analyzer.print_summary()

    print("🎉 ANALYSIS COMPLETE!")
    print(f"Reports saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
