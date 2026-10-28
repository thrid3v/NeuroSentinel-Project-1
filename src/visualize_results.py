import pandas as pd
import pickle
import json
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix

# --- CONFIG ---
DATA_PATH = "data/dataset.csv"
MODEL_PATH = "models/neuro_model.pkl"
METRICS_PATH = "models/metrics.json"

# 1. Load Data and Model
df = pd.read_csv(DATA_PATH)
with open(MODEL_PATH, 'rb') as f:
    model = pickle.load(f)
with open(METRICS_PATH, 'r') as f:
    metrics = json.load(f)

X = df.drop(['label', 'filename'], axis=1)
y = (df['label'] == 2).astype(int)  # 0=Healthy (incl. MCI), 1=Dementia - see train_model.py

# 2. Use the saved confusion matrix counts directly - train_model.py computes
# these from out-of-fold cross-validated probabilities at the decision
# threshold actually used in production, which is far more honest than
# re-splitting here and scoring a freshly refit model on one lucky/unlucky split.
full_metrics = metrics["full_model"]
cm = [[full_metrics["true_negatives"], full_metrics["false_positives"]],
      [full_metrics["false_negatives"], full_metrics["true_positives"]]]
labels = ["Healthy", "Dementia"]

# 3. Plot the Heatmap
plt.figure(figsize=(8, 6))
sns.set_theme(style="whitegrid")
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=labels, yticklabels=labels)

plt.title(
    f"Sensitivity: {full_metrics['sensitivity']*100:.0f}% | Specificity: {full_metrics['specificity']*100:.0f}% "
    f"(threshold={metrics['dementia_probability_threshold']})",
    fontsize=14, pad=20
)
plt.xlabel("AI Prediction", fontsize=12)
plt.ylabel("Actual Clinical Diagnosis", fontsize=12)
plt.savefig("models/confusion_matrix.png")
print("✅ Heatmap saved to models/confusion_matrix.png")
plt.show()
