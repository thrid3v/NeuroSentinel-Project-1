import os
import json
import pandas as pd
import numpy as np
import librosa
from vosk import Model, KaldiRecognizer

# --- CONFIGURATION ---
# Source data lives outside the repo (it's a third-party research corpus,
# not ours to redistribute) - point these at wherever you've placed it.
# CSV must have columns: Record-ID, Class (values: HC / MCI / Dementia).
# Audio layout expected: <EXTERNAL_AUDIO_ROOT>/<Record-ID>/<Record-ID>__CTD.wav
EXTERNAL_CSV_PATH = r"C:\Users\thrid\Downloads\Data_AUG_13.11.2024_output.csv"
EXTERNAL_AUDIO_ROOT = r"C:\Users\thrid\Desktop\congnitive_decline_dataset\Archive"

MODEL_PATH = "models/vosk-model-small-en-us-0.15"
OUTPUT_CSV = "data/dataset.csv"

LABELS_MAP = {"HC": 0, "MCI": 1, "Dementia": 2}

# --- 1. LOAD MODEL ---
if not os.path.exists(MODEL_PATH):
    print(f"❌ CRITICAL ERROR: Model not found at {MODEL_PATH}")
    exit(1)

print("Loading Vosk Model...")
model = Model(MODEL_PATH)

def analyze_audio(file_path):
    try:
        # PART A: ACOUSTIC & PROSODIC ANALYSIS
        y, sr = librosa.load(file_path, sr=16000)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfcc)  # Mean across all 13 coefficients - must match predictor.py
        mfcc_delta = np.mean(librosa.feature.delta(mfcc))
        spec_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_values = pitches[pitches > 0]
        emotional_range = np.var(pitch_values) if len(pitch_values) > 0 else 0

        # PART B: LINGUISTIC TIMING
        # Feed Vosk the audio librosa already loaded/resampled above, as raw
        # 16-bit PCM, instead of re-opening the file with the stdlib `wave`
        # module - `wave` only understands integer PCM WAV and raises
        # `wave.Error: unknown format: 3` outright on float32 WAV (see
        # predictor.py's extract_features_from_audio for the full story).
        pcm_bytes = (np.clip(y, -1.0, 1.0) * 32767).astype(np.int16).tobytes()

        rec = KaldiRecognizer(model, sr)
        rec.SetWords(True)
        results = []
        chunk_size = 8000  # bytes; matches the previous 4000-sample chunking (2 bytes/sample)
        for i in range(0, len(pcm_bytes), chunk_size):
            chunk = pcm_bytes[i:i + chunk_size]
            if rec.AcceptWaveform(chunk):
                part = json.loads(rec.Result())
                if 'result' in part: results.extend(part['result'])

        final_part = json.loads(rec.FinalResult())
        if 'result' in final_part: results.extend(final_part['result'])

        if not results: return None

        # FEATURE EXTRACTION
        initial_latency = results[0]['start']
        total_duration = results[-1]['end'] - results[0]['start']
        pause_time = sum([results[i+1]['start'] - results[i]['end']
                         for i in range(len(results) - 1)
                         if (results[i+1]['start'] - results[i]['end']) > 0.25])

        pause_rate = pause_time / total_duration if total_duration > 0 else 0
        words = [w['word'] for w in results]
        ttr = len(set(words)) / len(words) if words else 0
        speech_rate = len(words) / results[-1]['end'] if results[-1]['end'] > 0 else 0

        return {
            "pause_rate": round(pause_rate, 3),
            "vocab_richness": round(ttr, 3),
            "word_count": len(words),
            "initial_latency": round(initial_latency, 3),
            "acoustic_texture": round(mfcc_mean, 3),
            "speech_brightness": round(spec_centroid, 3),
            "mfcc_delta": round(mfcc_delta, 4),
            "emotional_range": round(emotional_range, 3),
            "speech_rate": round(speech_rate, 3)
        }
    except Exception as e:
        return None

# --- 2. PROCESSING LOOP WITH TRACKING ---
if not os.path.exists(EXTERNAL_CSV_PATH):
    print(f"❌ CRITICAL ERROR: Source CSV not found at {EXTERNAL_CSV_PATH}")
    exit(1)

labels_df = pd.read_csv(EXTERNAL_CSV_PATH)

data_records = []
scan_stats = {label: 0 for label in LABELS_MAP.keys()}

print(f"\n📂 Scanning '{EXTERNAL_AUDIO_ROOT}' for CTD audio files (per {EXTERNAL_CSV_PATH})...")

for _, row in labels_df.iterrows():
    record_id = row['Record-ID']
    class_name = row['Class']

    if class_name not in LABELS_MAP:
        print(f"⚠️  Skipping {record_id}: unknown class '{class_name}'.")
        continue

    file_path = os.path.join(EXTERNAL_AUDIO_ROOT, record_id, f"{record_id}__CTD.wav")
    if not os.path.exists(file_path):
        print(f"⚠️  Skipping {record_id}: CTD audio not found.")
        continue

    features = analyze_audio(file_path)
    if features:
        features['label'] = LABELS_MAP[class_name]
        features['filename'] = f"{record_id}__CTD.wav"
        data_records.append(features)
        scan_stats[class_name] += 1
        print(f"   ✅ {record_id} processed ({class_name}).")
    else:
        print(f"   ❌ {record_id} FAILED (no speech detected or bad audio format).")

# --- 3. FINAL SUMMARY TABLE ---
print("\n" + "="*40)
print(f"{'CATEGORY':<15} | {'FILES PROCESSED':<15}")
print("-" * 40)
for label, count in scan_stats.items():
    print(f"{label:<15} | {count:<15}")
print("-" * 40)
print(f"{'TOTAL':<15} | {len(data_records):<15} / {len(labels_df)} Expected")
print("="*40 + "\n")

if data_records:
    df = pd.DataFrame(data_records)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"🚀 SUCCESS! Dataset saved with all available parameters.")
else:
    print("🛑 ERROR: No data extracted. Check EXTERNAL_CSV_PATH / EXTERNAL_AUDIO_ROOT.")
