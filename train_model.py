"""
train_model.py  –  Train the CatBoost model for DataQuest hackathon.

Imports preprocess() from solution.py so training features
are guaranteed to match the judge's inference pipeline.

Output: model.pkl
"""

import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, classification_report
from catboost import CatBoostClassifier, Pool

# ---- Import our EXACT preprocess logic ----
from solution import preprocess


def main():
    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    print("📂  Loading train.csv …")
    df = pd.read_csv("train.csv")
    print(f"   Rows: {len(df):,}   Cols: {df.shape[1]}")

    # ------------------------------------------------------------------
    # 2. Preprocess the FULL dataframe (including target).
    #    This is critical because preprocess() calls drop_duplicates(),
    #    which can remove rows. If we split target first, X and y
    #    end up with different lengths.
    # ------------------------------------------------------------------
    TARGET = "Purchased_Coverage_Bundle"
    print("⚙️   Preprocessing …")
    df_processed = preprocess(df)                 # target survives (not dropped)
    print(f"   Rows after drop_duplicates: {len(df_processed):,}")

    y = df_processed[TARGET]
    X = df_processed.drop(columns=[TARGET, "User_ID"], errors="ignore")
    print(f"   Features: {X.shape[1]}")

    # ------------------------------------------------------------------
    # 3. Categorical columns (must match what CatBoost will see at inference)
    # ------------------------------------------------------------------
    CAT_COLS = [
        "Region_Code",
        "Broker_Agency_Type",
        "Deductible_Tier",
        "Acquisition_Channel",
        "Payment_Schedule",
        "Employment_Status",
        "Policy_Start_Month",
    ]
    cat_features = [c for c in CAT_COLS if c in X.columns]

    # CatBoost needs categoricals as str
    for c in cat_features:
        X[c] = X[c].astype(str)

    print(f"   Categorical features ({len(cat_features)}): {cat_features}")

    # ------------------------------------------------------------------
    # 4. Stratified train / validation split
    # ------------------------------------------------------------------
    X_train, X_val, y_train, y_val = train_test_split(
        X, y,
        test_size=0.15,
        random_state=42,
        stratify=y,
    )
    print(f"   Train: {len(X_train):,}   Val: {len(X_val):,}")

    # ------------------------------------------------------------------
    # 6. Build CatBoost pools
    # ------------------------------------------------------------------
    train_pool = Pool(X_train, label=y_train, cat_features=cat_features)
    val_pool   = Pool(X_val,   label=y_val,   cat_features=cat_features)

    # ------------------------------------------------------------------
    # 7. Train
    # ------------------------------------------------------------------
    model = CatBoostClassifier(
        loss_function="MultiClass",
        eval_metric="TotalF1:average=Macro",
        iterations=3000,
        depth=8,
        learning_rate=0.05,
        early_stopping_rounds=150,
        l2_leaf_reg=3,
        thread_count=-1,
        random_seed=42,
        verbose=100,
    )

    print("\n🚀  Training CatBoost …\n")
    model.fit(train_pool, eval_set=val_pool)

    # ------------------------------------------------------------------
    # 8. Evaluate on validation set
    # ------------------------------------------------------------------
    y_pred = model.predict(X_val).ravel()
    macro_f1 = f1_score(y_val, y_pred, average="macro")
    print(f"\n📊  Validation Macro-F1: {macro_f1:.4f}\n")
    print(classification_report(y_val, y_pred))

    # ------------------------------------------------------------------
    # 9. Save model  (joblib .pkl — allowed by the judge)
    # ------------------------------------------------------------------
    joblib.dump(model, "model.pkl")
    print("💾  Model saved → model.pkl")

    # Quick size check
    import os
    size_mb = os.path.getsize("model.pkl") / (1024 * 1024)
    print(f"   Model size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
