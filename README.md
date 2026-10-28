# NeuroSentinel - Cognitive Assessment Dashboard

![Version](https://img.shields.io/badge/version-1.2-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)

**NeuroSentinel** is an AI-powered cognitive assessment system that analyzes speech patterns to detect early signs of cognitive decline. The system extracts 9 neurological biomarkers from voice recordings and uses machine learning to classify cognitive health status as **Healthy** or **Dementia**.

**Live demo:** https://devoops-eq2x4aewddar6wxa3qmwk6.streamlit.app/

---

## Quick Start

### Prerequisites
- Python 3.8 or higher
- Microphone access (for live recording)
- ~200MB disk space (the two bundled Vosk speech-recognition models)

### Windows: one-click launch
Double-click **`Run_NeuroSentinel.bat`**. It checks for Python, installs dependencies on first run, pre-seeds Streamlit's one-time email prompt (which would otherwise block a double-clicked launch waiting for keyboard input), and opens the app in your browser.

### Manual setup (any OS)

1. **Install system dependencies** (required for audio processing)

   **macOS:** `brew install ffmpeg libsndfile`

   **Ubuntu/Debian:** `sudo apt-get install ffmpeg libsndfile1`

   **Windows:** install [FFmpeg](https://ffmpeg.org/download.html) or `choco install ffmpeg`

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**
   ```bash
   cd src
   streamlit run app.py
   ```
   Opens at `http://localhost:8501`. The trained models, scalers, and both Vosk speech models already ship in `models/`, so no separate download is needed for the English model.

### Optional: retrain the model

The model is trained on real clinical speech recordings (Cookie Theft picture-description task). The source audio is a third-party research dataset and is not redistributed here — only the derived, de-identified biomarkers are (`data/dataset.csv`).

```bash
python src/extract_features.py   # -> data/dataset.csv (biomarkers only, no raw audio/PII)
python src/train_model.py        # -> models/neuro_model.pkl, models/scaler.pkl
```

Edit `EXTERNAL_CSV_PATH` and `EXTERNAL_AUDIO_ROOT` at the top of `src/extract_features.py` first, to point at your own labeled CSV (`Record-ID`, `Class` columns, `Class` in `HC`/`MCI`/`Dementia`) and matching audio folder.

---

## 9-Point Neurological Biomarker Panel

Each recording is scored on 9 biomarkers across acoustic, prosodic, and linguistic dimensions:

| # | Biomarker | What it measures | Healthy range |
|---|-----------|-------------------|----------------|
| 1 | Pause Rate | `pause_time / total_duration` (pauses > 0.25s) | < 0.35 |
| 2 | Vocabulary Richness (TTR) | `unique_words / total_words` | > 0.55 |
| 3 | Word Count | Total words transcribed | > 80 words |
| 4 | Speech Rate | `word_count / total_duration` | > 1.9 words/sec |
| 5 | Initial Latency | Time to first word | < 3.0 sec |
| 6 | Acoustic Texture | Mean of all 13 MFCCs | > -30 |
| 7 | MFCC Delta | Mean spectral rate-of-change | \|delta\| < 0.015 |
| 8 | Speech Brightness | Spectral centroid | > 1600 Hz |
| 9 | Emotional Range | Pitch (F0) variance | > 1,000,000 |

Ranges are mean − 1 std of the real Healthy class in `data/dataset.csv`, not arbitrary cutoffs. Clinical rationale for each biomarker is documented inline in `src/predictor.py` and `src/extract_features.py`.

---

## Machine Learning

### Primary model (English)
- **Algorithm:** Random Forest (`sklearn.ensemble.RandomForestClassifier`), binary output
- **Training data:** 157 real clinical recordings — 82 Healthy + 59 MCI (folded into "Healthy") vs. 16 Dementia
- **Preprocessing:** StandardScaler
- **Tuning:** `GridSearchCV`, 5-fold CV, scored on `balanced_accuracy`
- **Decision rule:** reports "Dementia" only when P(Dementia) ≥ **0.40** (see `models/metrics.json`); otherwise "Healthy"

### Speech recognition
[Vosk](https://alphacephei.com/vosk/) (Kaldi-based ASR): `vosk-model-small-en-us-0.15` (English, primary) and `vosk-model-small-hi-0.22` (Hindi, experimental).

### Hindi support (experimental, unvalidated)
No labeled Hindi cognitive-decline dataset exists publicly, so Hindi recordings are transcribed with the Hindi Vosk model, but only the **4 waveform-derived biomarkers** (acoustic texture, MFCC delta, speech brightness, emotional range) feed the decision — via a separate acoustic-only Random Forest (`models/neuro_model_acoustic.pkl`), trained on the same English data. The 5 ASR-derived biomarkers are shown for information only, because the only Hindi reference audio available to calibrate them (OpenSLR SLR103) was short, scripted, 8kHz telephone-bandwidth recordings — not comparable to this app's spontaneous-narration task, and lacking the frequency content the acoustic biomarkers need. This architecture is a defensible design choice, not something empirically validated on real spontaneous Hindi speech. Full reasoning is in `src/predictor.py`.

To enable Hindi mode, nothing extra is needed — `models/vosk-model-small-hi-0.22/` already ships in this repo.

---

## Why only "Healthy" / "Dementia" (no "MCI")

Early testing with a 3-class model flagged ordinary conversational hesitation as "MCI." Instead, MCI recordings are folded into the "Healthy" training label, and the binary decision is deliberately conservative — "Dementia" only above a 0.40 probability threshold:

| Threshold | Sensitivity | Specificity |
|---|---|---|
| 0.30 | 44% | 75% |
| **0.40 (current)** | **31%** | **87%** |
| 0.50 | 12% | 93% |

With only 16 real Dementia examples in training, no threshold is both sensitive and conservative — a real data limitation, not a tunable bug. **This is a screening aid tuned to avoid alarming healthy users, not a tool that rules out dementia.** A "Healthy" result does not mean decline has been ruled out.

When a result is "Healthy," the app separately checks recording quality (duration, volume, pace) and surfaces tips like *"Recording was quite short"* when the recording itself — not necessarily cognition — may have affected the result.

---

## Project Structure

```
.
├── src/
│   ├── app.py                      # Streamlit app (3 tabs: Assessment, Biomarkers, History)
│   ├── predictor.py                # Feature extraction + prediction engine
│   ├── extract_features.py         # Batch feature extraction from an external labeled dataset
│   ├── train_model.py              # Model training + hyperparameter tuning
│   ├── generate_synthetic_data.py  # Legacy, unused by default
│   ├── db.py                       # SQLite operations
│   ├── report.py                   # PDF report generation
│   └── visualize_results.py        # Confusion matrix plotting
├── models/
│   ├── neuro_model.pkl / scaler.pkl                  # Full 9-feature model (English)
│   ├── neuro_model_acoustic.pkl / scaler_acoustic.pkl # 4-feature model (Hindi)
│   ├── metrics.json                # Cross-validated sensitivity/specificity, not training accuracy
│   ├── vosk-model-small-en-us-0.15/
│   └── vosk-model-small-hi-0.22/
├── data/dataset.csv                # Extracted biomarkers + labels (no raw audio/PII)
├── requirements.txt
└── Run_NeuroSentinel.bat           # Windows one-click launcher
```

---

## Model Performance

Accuracy is deliberately not reported anywhere in the app: with 141 Healthy vs. 16 Dementia (~90/10 split), a model that always predicts "Healthy" would score ~90% accuracy while being useless. Instead, performance is reported as **sensitivity** and **specificity** from repeated cross-validation (5-fold × 20 repeats = 100 out-of-fold evaluations, since 16 positive examples is too few for a single train/test split to be reliable):

| Model | Sensitivity | Specificity |
|---|---|---|
| Full 9-feature (English) | 31% | 87% |
| Acoustic-only (Hindi) | 25% | 97% |

See `models/metrics.json` for exact true/false positive/negative counts.

---

## Database Schema

SQLite table `records`: `id`, `timestamp`, `patient_id`, `risk_label`, `confidence`, and one column per biomarker (`pause_rate`, `vocab_richness`, `word_count`, `speech_rate`, `initial_latency`, `acoustic_texture`, `mfcc_delta`, `speech_brightness`, `emotional_range`). See `src/db.py`.

---

## Privacy

All processing runs locally — no audio or results are sent to an external server. The SQLite database (`neuro.db`) and generated PDF reports stay on disk and are gitignored, not committed to this repo.

---

## Limitations

- **Not a diagnostic tool** — research/screening use only; confirm findings with a clinical professional
- **Small, imbalanced training set** — 157 recordings, only 16 Dementia examples; sensitivity/specificity estimates carry real uncertainty
- **Single elicitation task** — trained only on the Cookie Theft picture-description task
- **Hindi mode is unvalidated** on real spontaneous Hindi speech, in either direction
- **Audio quality matters** — clear recordings in quiet environments work best

---

## Dependencies

```
streamlit, pandas, plotly, numpy>=2.0, librosa, vosk, scikit-learn==1.9.0, fpdf
```

`numpy>=2.0` and the exact `scikit-learn==1.9.0` pin matter: the shipped `.pkl` files were pickled under those versions, and unpickling across a numpy 1.x/2.x boundary fails outright. See comments in `requirements.txt`.

---

## References

- König et al. (2015) — pause rate and cognitive decline
- Fraser et al. (2016) — lexical diversity in dementia
- Skodda et al. (2011) — acoustic features in neurodegeneration
- [Librosa](https://librosa.org/) · [Vosk](https://alphacephei.com/vosk/) · [scikit-learn](https://scikit-learn.org/) · [Streamlit](https://streamlit.io/)
