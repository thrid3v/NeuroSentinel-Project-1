import pandas as pd
import numpy as np
import os

# CONFIG
INPUT_PATH = "data/dataset.csv"
OUTPUT_PATH = "data/synthetic_dataset.csv"
SAMPLES_PER_CLASS = 500  # Generate 500 samples for EACH of the 4 classes (Healthy, Mild, Moderate, Severe)

def generate_synthetic_data():
    if not os.path.exists(INPUT_PATH):
        print(f"❌ Error: {INPUT_PATH} not found.")
        return

    print(f"Loading seed data from {INPUT_PATH}...")
    df = pd.read_csv(INPUT_PATH)
    
    # Identify feature columns (everything except label and filename)
    feature_cols = [c for c in df.columns if c not in ['label', 'filename']]
    
    synthetic_data = []
    
    # Iterate through each class (0, 1, 2, 3)
    for label in sorted(df['label'].unique()):
        print(f"  - Processing Class {label}...")
        
        # Get subset for this class
        class_df = df[df['label'] == label]
        
        if class_df.empty:
            print(f"    ⚠️ Warning: No data for class {label}. Skipping.")
            continue
            
        # Calculate statistics
        stats = class_df[feature_cols].agg(['mean', 'std']).to_dict()
        
        # Generate new samples
        new_samples = {}
        for feature in feature_cols:
            mean = stats[feature]['mean']
            std = stats[feature]['std']
            
            # handle case where std is NaN (if only 1 sample exists) or 0
            if pd.isna(std) or std == 0:
                std = 0.01 * (abs(mean) if mean != 0 else 1.0) # Add tiny noise if variance is zero
                
            # Generate random values from Gaussian distribution
            values = np.random.normal(loc=mean, scale=std, size=SAMPLES_PER_CLASS)
            new_samples[feature] = values
            
        # Create DataFrame for this class
        batch_df = pd.DataFrame(new_samples)
        batch_df['label'] = label
        batch_df['filename'] = f"synthetic_class_{label}" # Placeholder
        
        synthetic_data.append(batch_df)
        
    # Combine all
    final_df = pd.concat(synthetic_data, ignore_index=True)
    
    # Shuffle
    final_df = final_df.sample(frac=1).reset_index(drop=True)
    
    # Save
    final_df.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Generated {len(final_df)} synthetic samples.")
    print(f"💾 Saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_synthetic_data()
