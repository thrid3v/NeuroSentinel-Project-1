import pandas as pd
import pickle
import os
import json
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, RepeatedStratifiedKFold, cross_val_score
from sklearn.metrics import confusion_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


# --- CONFIG ---
DATA_PATH = "data/dataset.csv"
MODEL_PATH = "models/neuro_model.pkl"
SCALER_PATH = "models/scaler.pkl"
METRICS_PATH = "models/metrics.json"

# The 4 biomarkers computed straight from the waveform (Librosa), with no
# ASR/transcription involved - the only features that are genuinely
# language-independent. Used for a second model trained specifically for
# cross-lingual (Hindi) scoring - see the bottom of this script for why.
ACOUSTIC_FEATURES = ["acoustic_texture", "mfcc_delta", "speech_brightness", "emotional_range"]
ACOUSTIC_MODEL_PATH = "models/neuro_model_acoustic.pkl"
ACOUSTIC_SCALER_PATH = "models/scaler_acoustic.pkl"

# Only two output labels: Healthy or Dementia - no "MCI"/"mild" label is ever
# shown. MCI is folded into the Healthy bucket for training (not into
# Dementia): clinically MCI's speech patterns sit much closer to normal than
# to dementia, and the goal here is "only flag when it strongly looks like
# dementia" - lumping MCI in with Dementia would train the model to flag
# exactly the borderline/subtle cases we're trying to stay quiet about.
DEMENTIA_PROBABILITY_THRESHOLD = 0.40  # see README "Model Performance" for the
# sensitivity/specificity trade-off this was chosen from - chosen with the user.

# 1. Load Data
if not os.path.exists(DATA_PATH):
    print(f"❌ Error: {DATA_PATH} not found.")
    exit()

df = pd.read_csv(DATA_PATH)

# 2. Prepare Features (X) and binary Labels (y): 0=Healthy (HC + MCI), 1=Dementia
X = df.drop(['label', 'filename'], axis=1)
y = (df['label'] == 2).astype(int)

print(f"Binary class counts (0=Healthy incl. MCI, 1=Dementia): {y.value_counts().sort_index().to_dict()}")

param_grid = {
    'n_estimators': [200, 500],
    'max_depth': [10, 20, None],
    'min_samples_split': [2, 5],
    'class_weight': ['balanced', None]
}

# Same repeated stratified CV scheme used for both models below, and for
# computing out-of-fold probabilities to pick the decision threshold - with
# only 16 Dementia samples total, a single train/test split is far too noisy
# to trust (see README).
cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=20, random_state=42)


def train_and_evaluate(X_features, label):
    """Grid-searches hyperparameters, computes out-of-fold predicted
    probabilities for every sample (averaged across the repeats each sample
    appears in a test fold), and reports sensitivity/specificity at
    DEMENTIA_PROBABILITY_THRESHOLD - NOT plain accuracy, which is close to
    meaningless on a ~90/10 imbalanced binary problem (predicting "Healthy"
    for everyone already scores ~90%)."""
    print("-" * 30)
    print(f"🧠 Searching for the optimal brain configuration ({label})...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_features)

    grid_search = GridSearchCV(
        RandomForestClassifier(random_state=42),
        param_grid,
        cv=5,
        scoring='balanced_accuracy',
        n_jobs=-1
    )
    grid_search.fit(X_scaled, y)
    model = grid_search.best_estimator_
    print(f"Best Params: {grid_search.best_params_}")

    pipe = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', RandomForestClassifier(random_state=42, **grid_search.best_params_))
    ])

    probs = np.zeros(len(y))
    counts = np.zeros(len(y))
    for train_idx, test_idx in cv.split(X_features, y):
        pipe.fit(X_features.iloc[train_idx], y.iloc[train_idx])
        p = pipe.predict_proba(X_features.iloc[test_idx])[:, 1]
        probs[test_idx] += p
        counts[test_idx] += 1
    avg_probs = probs / counts

    preds = (avg_probs >= DEMENTIA_PROBABILITY_THRESHOLD).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, preds).ravel()
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    print(f"   At threshold {DEMENTIA_PROBABILITY_THRESHOLD}: sensitivity={sensitivity*100:.1f}% "
          f"({tp}/{tp+fn} real Dementia cases caught), specificity={specificity*100:.1f}% "
          f"({tn}/{tn+fp} Healthy/MCI correctly left alone), {fp} false alarms")

    print("🧠 Clinical Biomarker Weights:")
    for feature, importance in sorted(zip(X_features.columns, model.feature_importances_), key=lambda x: x[1], reverse=True):
        print(f"   - {feature}: {importance:.3f}")

    metrics_out = {
        "best_params": {k: v for k, v in grid_search.best_params_.items()},
        "sensitivity": round(float(sensitivity), 4),
        "specificity": round(float(specificity), 4),
        "true_positives": int(tp),
        "false_negatives": int(fn),
        "true_negatives": int(tn),
        "false_positives": int(fp),
    }
    return model, scaler, metrics_out


model, scaler, main_metrics = train_and_evaluate(X, "full 9-feature model")

with open(MODEL_PATH, 'wb') as f:
    pickle.dump(model, f)
with open(SCALER_PATH, 'wb') as f:
    pickle.dump(scaler, f)

metrics = {
    "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "n_samples": int(len(df)),
    "class_counts": {"Healthy": int((y == 0).sum()), "Dementia": int((y == 1).sum())},
    "dementia_probability_threshold": DEMENTIA_PROBABILITY_THRESHOLD,
    "full_model": main_metrics,
}
with open(METRICS_PATH, 'w') as f:
    json.dump(metrics, f, indent=2)

print(f"\n💾 Model, scaler, and metrics saved.")

# --- SECOND MODEL: acoustic-only, for cross-lingual (Hindi) scoring ---
# The 5 ASR-derived features (pause_rate, vocab_richness, word_count,
# speech_rate, initial_latency) depend on language-specific transcription
# and can't be calibrated cross-lingually with the data available (the only
# Hindi reference audio found is short read-speech ASR-benchmark clips,
# nothing length/task-matched to the live assessment's spontaneous
# narrative). Hindi mode uses a separate model trained only on the 4
# acoustic features, which need no cross-lingual correction since they're
# computed straight from the waveform.
X_acoustic = df[ACOUSTIC_FEATURES]
acoustic_model, acoustic_scaler, acoustic_metrics = train_and_evaluate(X_acoustic, "acoustic-only model (Hindi)")

with open(ACOUSTIC_MODEL_PATH, 'wb') as f:
    pickle.dump(acoustic_model, f)
with open(ACOUSTIC_SCALER_PATH, 'wb') as f:
    pickle.dump(acoustic_scaler, f)

metrics["acoustic_model"] = acoustic_metrics
with open(METRICS_PATH, 'w') as f:
    json.dump(metrics, f, indent=2)

print(f"💾 Acoustic-only model and scaler saved (used for Hindi scoring).")
