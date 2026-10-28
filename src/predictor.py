import os
import json
import pickle
import numpy as np
import pandas as pd
import librosa
from vosk import Model, KaldiRecognizer

# --- DYNAMIC PATH SETUP (THE FIX) ---
# Get the directory where THIS file (predictor.py) is located
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Go up one level to the project root (neuro-sentinel/)
ROOT_DIR = os.path.dirname(CURRENT_DIR)

# Construct absolute paths that work on both Windows and Cloud
VOSK_EN_PATH = os.path.join(ROOT_DIR, "models", "vosk-model-small-en-us-0.15")
VOSK_HI_PATH = os.path.join(ROOT_DIR, "models", "vosk-model-small-hi-0.22")
MODEL_PATH = os.path.join(ROOT_DIR, "models", "neuro_model.pkl")
SCALER_PATH = os.path.join(ROOT_DIR, "models", "scaler.pkl")
METRICS_PATH = os.path.join(ROOT_DIR, "models", "metrics.json")

# Acoustic-only model (4 waveform-derived features), used for Hindi/
# cross-lingual scoring instead of the full 9-feature model - see
# train_model.py for why the 5 ASR-derived features aren't used cross-lingually.
ACOUSTIC_MODEL_PATH = os.path.join(ROOT_DIR, "models", "neuro_model_acoustic.pkl")
ACOUSTIC_SCALER_PATH = os.path.join(ROOT_DIR, "models", "scaler_acoustic.pkl")
ACOUSTIC_FEATURES = ["acoustic_texture", "mfcc_delta", "speech_brightness", "emotional_range"]

# Exact column order the full model was trained on. extract_features_from_audio
# also returns diagnostic-only columns (duration_s, rms) for the recording-
# quality check below - this list is how we slice back down to just what the
# model/scaler expect before scoring, regardless of what else is in the frame.
FULL_FEATURES = [
    "pause_rate", "vocab_richness", "word_count", "initial_latency",
    "acoustic_texture", "speech_brightness", "mfcc_delta",
    "emotional_range", "speech_rate",
]

DEFAULT_DEMENTIA_THRESHOLD = 0.40

# --- 1. LOAD MODELS ---
print(f"🔎 Looking for models in: {os.path.join(ROOT_DIR, 'models')}")

clf = None
scaler = None
vosk_model_en = None
vosk_model_hi = None

# Load Vosk (English)
if not os.path.exists(VOSK_EN_PATH):
    # Fallback: Sometimes Cloud puts models in src/models
    VOSK_EN_PATH = os.path.join(CURRENT_DIR, "models", "vosk-model-small-en-us-0.15")

if os.path.exists(VOSK_EN_PATH):
    try:
        vosk_model_en = Model(VOSK_EN_PATH)
        print("✅ Vosk EN Model Loaded!")
    except Exception as e:
        print(f"❌ Vosk EN Load Error: {e}")
else:
    print(f"⚠️ CRITICAL: Vosk EN model not found at {VOSK_EN_PATH}")

# Load Vosk (Hindi) — optional; Hindi mode degrades gracefully if absent
if not os.path.exists(VOSK_HI_PATH):
    VOSK_HI_PATH = os.path.join(CURRENT_DIR, "models", "vosk-model-small-hi-0.22")

if os.path.exists(VOSK_HI_PATH):
    try:
        vosk_model_hi = Model(VOSK_HI_PATH)
        print("✅ Vosk HI Model Loaded!")
    except Exception as e:
        print(f"❌ Vosk HI Load Error: {e}")
else:
    print(f"ℹ️ Vosk HI model not found at {VOSK_HI_PATH} — Hindi mode unavailable until it is downloaded.")


def _get_vosk_model(language="en"):
    return vosk_model_hi if language == "hi" else vosk_model_en


def is_hindi_available():
    return vosk_model_hi is not None


def is_model_loaded():
    """False if the classifier failed to load (e.g. a dependency version
    mismatch between training and deployment, like the numpy 2.x/1.x pickle
    incompatibility this project hit once already - see requirements.txt).
    Checking this at startup surfaces that immediately instead of only after
    a user runs an analysis and gets a generic 'could not extract' error."""
    return clf is not None


acoustic_clf = None
acoustic_scaler = None

# Load Classifier & Scaler
try:
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, 'rb') as f:
            clf = pickle.load(f)
            print("✅ Classifier Loaded!")
    else:
        print(f"⚠️ Classifier not found at {MODEL_PATH}")

    if os.path.exists(SCALER_PATH):
        with open(SCALER_PATH, 'rb') as f:
            scaler = pickle.load(f)
            print("✅ Scaler Loaded!")

    if os.path.exists(ACOUSTIC_MODEL_PATH):
        with open(ACOUSTIC_MODEL_PATH, 'rb') as f:
            acoustic_clf = pickle.load(f)
            print("✅ Acoustic-only Classifier Loaded!")
    else:
        print(f"⚠️ Acoustic-only classifier not found at {ACOUSTIC_MODEL_PATH} — Hindi mode will fall back to the full model.")

    if os.path.exists(ACOUSTIC_SCALER_PATH):
        with open(ACOUSTIC_SCALER_PATH, 'rb') as f:
            acoustic_scaler = pickle.load(f)
            print("✅ Acoustic-only Scaler Loaded!")
except Exception as e:
    print(f"⚠️ Model/Scaler Load Error: {e}")

# The probability threshold above which a result is reported as "Dementia" -
# below it, the result is "Healthy" (there is no third "MCI"/"mild" label).
# Loaded from the value train_model.py actually used, so the app can't drift
# out of sync with what was validated.
DEMENTIA_THRESHOLD = DEFAULT_DEMENTIA_THRESHOLD
if os.path.exists(METRICS_PATH):
    try:
        with open(METRICS_PATH, 'r') as f:
            DEMENTIA_THRESHOLD = json.load(f).get("dementia_probability_threshold", DEFAULT_DEMENTIA_THRESHOLD)
    except Exception:
        pass


def generate_clinical_summary(features_df):
    """Generates softer, elderly-friendly clinical observations."""
    try:
        if features_df is None or features_df.empty:
            return "No data available for summary."

        # Extract values safely
        p_rate = features_df['pause_rate'].iloc[0]
        s_rate = features_df.get('speech_rate', pd.Series([0])).iloc[0]
        
        observations = []
        # Using supportive, clinical language
        if p_rate > 0.35:
            observations.append("Observed slight hesitations in natural speech rhythm.")
        if s_rate < 1.9 and s_rate > 0:
            observations.append("Speech tempo is currently below the standardized baseline.")
            
        if not observations:
            return "Speech biomarkers reflect a stable and healthy cognitive baseline."
        
        return " | ".join(observations)
    except Exception as e:
        return f"Summary generation error: {str(e)}"

def extract_features_from_audio(file_path, language="en"):
    """ Extracts all biomarkers using Librosa and Vosk """
    try:
        # 1. ACOUSTIC ANALYSIS (Librosa)
        y, sr = librosa.load(file_path, sr=16000)
        duration_s = len(y) / sr
        rms_db = float(librosa.amplitude_to_db(np.array([np.sqrt(np.mean(y**2)) + 1e-9]))[0])

        # MFCCs
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfcc) # Global mean
        mfcc_delta = np.mean(librosa.feature.delta(mfcc))
        
        # Spectral Centroid
        spec_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        
        # Pitch / Emotional Range
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_values = pitches[pitches > 0]
        emotional_range = np.var(pitch_values) if len(pitch_values) > 0 else 0
        
        # 2. LINGUISTIC ANALYSIS (Vosk)
        model_to_use = _get_vosk_model(language)
        if model_to_use is None:
            print(f"⚠️ No Vosk model available for language='{language}'.")
            return None

        # Feed Vosk the audio librosa already loaded/resampled above, as raw
        # 16-bit PCM, instead of re-opening the original file with the stdlib
        # `wave` module. `wave` only understands plain integer PCM WAV (format
        # tag 1) and raises `wave.Error: unknown format: 3` outright on
        # float32 WAV (format tag 3) - which is what browser-based recorders
        # (e.g. Streamlit's st.audio_input, via the Web Audio API) can
        # produce, since Web Audio natively works in float32. librosa/
        # soundfile handle that format fine, so reuse what already loaded
        # successfully rather than re-parsing the file a second, less capable
        # way. This also sidesteps the old silent sample-width mismatch case
        # (format check that printed a warning but fed Vosk the raw bytes
        # anyway, corrupting recognition if the original wasn't 16-bit PCM).
        pcm_bytes = (np.clip(y, -1.0, 1.0) * 32767).astype(np.int16).tobytes()

        rec = KaldiRecognizer(model_to_use, sr)
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

        if not results:
            print("No words detected by Vosk.")
            return None

        # Calculate Metrics
        initial_latency = results[0]['start']
        total_duration = results[-1]['end'] - results[0]['start']
        
        pause_time = 0.0
        for i in range(len(results) - 1):
            gap = results[i+1]['start'] - results[i]['end']
            if gap > 0.25:
                pause_time += gap
        
        pause_rate = pause_time / total_duration if total_duration > 0 else 0
        words = [w['word'] for w in results]
        ttr = len(set(words)) / len(words) if words else 0
        speech_rate = len(words) / total_duration if total_duration > 0 else 0
        
        # RETURN DATAFRAME - the 9 model features, plus duration_s/rms_db which
        # are diagnostic-only (recording-quality notes, not fed to any model;
        # callers slice down to FULL_FEATURES/ACOUSTIC_FEATURES before scoring)
        return pd.DataFrame([{
            "pause_rate": round(pause_rate, 3),
            "vocab_richness": round(ttr, 3),
            "word_count": len(words),
            "initial_latency": round(initial_latency, 3),
            "acoustic_texture": round(mfcc_mean, 3),
            "speech_brightness": round(spec_centroid, 3),
            "mfcc_delta": round(mfcc_delta, 4),
            "emotional_range": round(emotional_range, 3),
            "speech_rate": round(speech_rate, 3),
            "duration_s": round(duration_s, 2),
            "rms_db": round(rms_db, 2),
        }])

    except Exception as e:
        print(f"❌ Feature Extraction Error: {e}")
        return None

def assess_recording_quality(features_df, result_label):
    """Short, friendly notes about the recording itself - not a diagnostic
    claim. Point of this: a short/quiet/unusually-fast-or-slow recording can
    push biomarkers around for reasons that have nothing to do with
    cognition, so when the result isn't a confident Dementia flag, surface
    that possibility instead of silently treating a noisy reading as fact.
    Thresholds are set against the real English dataset's own recordings
    (typically 100s+, -22 to -28 dB) - see data/dataset.csv.
    """
    notes = []
    row = features_df.iloc[0]
    duration_s = row.get('duration_s')
    rms_db = row.get('rms_db')

    if duration_s is not None and duration_s < 15:
        notes.append("Recording was quite short - try speaking for 30-60 seconds next time for a more reliable result.")
    if row.get('word_count', 0) < 20:
        notes.append("Very few words were detected - try speaking a bit more.")
    if rms_db is not None and rms_db < -40:
        notes.append("Audio volume seemed low - try speaking closer to the microphone or in a quieter space.")

    # These two are about softening borderline-but-not-strongly-flagged
    # results, not about the recording per se - only shown when the result
    # itself is Healthy (i.e. the model wasn't confident enough to call it
    # Dementia), so it never looks like we're excusing an actual flag.
    if result_label == "Healthy":
        if row.get('speech_rate', 99) < 1.3:
            notes.append("Your speaking pace was slower than typical for this analysis - if that's not how you normally speak, try recording again at a natural pace.")
        if row.get('pause_rate', 0) > 0.5:
            notes.append("Longer pauses than typical were detected - background noise or thinking time can both cause this; try a quiet space if possible.")

    return notes


def get_prediction(audio_path, language="en"):
    """ Returns: (Label, Confidence, Features, Notes) """
    if clf is None:
        return "Model Error", 0.0, None, []

    features_df = extract_features_from_audio(audio_path, language=language)

    if features_df is None:
        return "Processing Error", 0.0, None, []

    # Hindi recordings are scored by the acoustic-only model (4 waveform
    # biomarkers, no ASR involved) instead of the full 9-feature model. The
    # 5 ASR-derived features depend on language-specific transcription and
    # there's no sound way to calibrate them cross-lingually with the Hindi
    # reference data available (see train_model.py) - using the acoustic-only
    # model sidesteps that rather than silently feeding in miscalibrated
    # values. The full 9-biomarker panel is still shown in the UI for
    # information, it just isn't what the Hindi classification decision uses.
    use_acoustic_only = (language == "hi" and acoustic_clf is not None)

    if use_acoustic_only:
        active_clf = acoustic_clf
        features_for_model = features_df[ACOUSTIC_FEATURES]
        active_scaler = acoustic_scaler
    else:
        active_clf = clf
        features_for_model = features_df[FULL_FEATURES]
        active_scaler = scaler

    # Scale features if scaler exists
    features_final = features_for_model
    if active_scaler is not None:
        try:
            features_final = active_scaler.transform(features_for_model)
        except Exception as e:
            print(f"Scaling warning: {e}")

    try:
        # Only two output labels, ever: Healthy or Dementia. "Dementia" fires
        # only when P(Dementia) clears DEMENTIA_THRESHOLD, not just whichever
        # class is more likely - deliberately conservative (see README) so
        # ordinary conversational pauses/hesitation don't get flagged as
        # decline. Below the threshold is reported as Healthy, period - there
        # is no intermediate "MCI"/"mild" label.
        dementia_probability = float(active_clf.predict_proba(features_final)[0][1])
        if dementia_probability >= DEMENTIA_THRESHOLD:
            result_text = "Dementia"
            confidence = dementia_probability
        else:
            result_text = "Healthy"
            confidence = 1.0 - dementia_probability

        notes = assess_recording_quality(features_df, result_text)

        return result_text, confidence, features_df, notes

    except Exception as e:
        print(f"Prediction logic error: {e}")
        return "Error", 0.0, features_df, []


def get_model_metrics():
    """Returns the honest, held-out performance metrics saved by train_model.py.

    Deliberately does NOT re-score the model against data/dataset.csv - that
    was the old approach (calculate_current_accuracy), and since that CSV is
    the same data the model was trained on, it reported near-training accuracy
    (~91%) next to a true held-out accuracy of ~56%. Always read the metrics
    file that was computed on data the model never saw during fitting.
    """
    if not os.path.exists(METRICS_PATH):
        return None
    try:
        with open(METRICS_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Metrics load error: {e}")
        return None
