import pandas as pd
import numpy as np
from solution import preprocess
# ==============================
# LOAD DATAe
# ==============================

from scipy.stats import ks_2samp

def drift_report(train, test, numeric_cols, alpha=0.01):
    results = []

    for c in numeric_cols:
        if c not in test.columns:
            continue

        stat, p = ks_2samp(train[c].dropna(), test[c].dropna())
        results.append((c, stat, p))

    df = pd.DataFrame(results, columns=["feature","ks_stat","p_value"])
    df = df.sort_values("p_value")

    print(df)

    drifted = df[df["p_value"] < alpha]

    print("\n--- Significant Drift ---")
    if len(drifted) == 0:
        print("No significant drift detected.")
    else:
        print(drifted)

train = pd.read_csv("train.csv")
raw = train
train = preprocess(train)
print("\n" + "="*60)
print("DATASET OVERVIEW")
print("="*60)

print("Shape:", train.shape)
print("\nData types:")
print(train.dtypes.value_counts())

# ==============================
# MISSING VALUES
# ==============================

print("\n" + "="*60)
print("MISSING VALUES")
print("="*60)

missing = train.isna().sum()
missing_pct = missing / len(train) * 100

missing_df = pd.DataFrame({
    "missing_count": missing,
    "missing_percent": missing_pct
}).sort_values("missing_percent", ascending=False)

print(missing_df[missing_df.missing_count > 0])

# ==============================
# DUPLICATES
# ==============================

print("\n" + "="*60)
print("DUPLICATES")
print("="*60)

print("Duplicate rows:", train.duplicated().sum())

# ==============================
# NUMERICAL STATISTICS
# ==============================

num_cols = train.select_dtypes(include=["int64","float64"]).columns

print("\n" + "="*60)
print("NUMERICAL SUMMARY")
print("="*60)

print(train[num_cols].describe().T)

# ==============================
# OUTLIER DETECTION (IQR)
# ==============================

print("\n" + "="*60)
print("OUTLIERS (IQR METHOD)")
print("="*60)

for col in num_cols:
    q1 = train[col].quantile(0.25)
    q3 = train[col].quantile(0.75)
    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    outliers = ((train[col] < lower) | (train[col] > upper)).sum()

    if outliers > 0:
        print(f"{col:35s} -> {outliers} outliers")

# ==============================
# EXTREME OUTLIERS (Z SCORE)
# ==============================

print("\n" + "="*60)
print("EXTREME OUTLIERS (|Z| > 3)")
print("="*60)

for col in num_cols:
    std = train[col].std()
    if std == 0:
        continue

    z = (train[col] - train[col].mean()) / std
    extreme = (np.abs(z) > 3).sum()

    if extreme > 0:
        print(f"{col:35s} -> {extreme} extreme values")

# ==============================
# LOGICAL ANOMALIES
# ==============================

print("\n" + "="*60)
print("LOGICAL ANOMALIES")
print("="*60)

checks = []

if "Estimated_Annual_Income" in train.columns:
    checks.append(("Negative income",
                   (train["Estimated_Annual_Income"] < 0).sum()))

if "Years_Without_Claims" in train.columns:
    checks.append(("Negative claim-free years",
                   (train["Years_Without_Claims"] < 0).sum()))

if "Adult_Dependents" in train.columns:
    checks.append(("Negative adult dependents",
                   (train["Adult_Dependents"] < 0).sum()))

if "Vehicles_on_Policy" in train.columns:
    checks.append(("Negative vehicles",
                   (train["Vehicles_on_Policy"] < 0).sum()))

for name, count in checks:
    if count > 0:
        print(f"{name}: {count}")

# ==============================
# CATEGORICAL ANALYSIS
# ==============================

cat_cols = train.select_dtypes(include=["object"]).columns

print("\n" + "="*60)
print("CATEGORICAL DISTRIBUTIONS")
print("="*60)

for col in cat_cols:
    print("\n---", col, "---")
    print("Unique values:", train[col].nunique())
    print(train[col].value_counts().head(10))

# ==============================
# RARE CATEGORIES
# ==============================

print("\n" + "="*60)
print("RARE CATEGORIES (<1%)")
print("="*60)

for col in cat_cols:
    freq = train[col].value_counts(normalize=True)
    rare = freq[freq < 0.01]

    if len(rare) > 0:
        print("\n", col)
        print(rare)

# ==============================
# HIGH CARDINALITY
# ==============================

print("\n" + "="*60)
print("HIGH CARDINALITY COLUMNS")
print("="*60)

for col in train.columns:
    nunique = train[col].nunique()
    if nunique > 100:
        print(f"{col:30s} -> {nunique} unique values")

# ==============================
# CONSTANT COLUMNS
# ==============================

print("\n" + "="*60)
print("CONSTANT COLUMNS")
print("="*60)

for col in train.columns:
    if train[col].nunique() <= 1:
        print(col)

print("\n" + "="*60)
print("AUDIT COMPLETE")
print("="*60)

# ==============================
# LOAD TEST DATA FOR DRIFT CHECK
# ==============================

test = pd.read_csv("test.csv")
test = preprocess(test)

# ==============================
# NUMERIC COLUMNS (COMMON ONLY)
# ==============================

numeric_cols = train.select_dtypes(include=["int64","float64"]).columns

# make sure both datasets share columns
numeric_cols = [c for c in numeric_cols if c in test.columns]

# ==============================
# RUN DRIFT DETECTION
# ==============================

print("\n" + "="*60)
print("TRAIN vs TEST DRIFT CHECK (KS TEST)")
print("="*60)

drift_report(train, test, numeric_cols)
