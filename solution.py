import os
import pandas as pd
import numpy as np
import joblib

# -------------------------------------------------------------------------
# Hardcoded training-set medians (from _compute_medians.py on train.csv).
# Used for NaN imputation — avoids computing median() at runtime (memory bomb).
# -------------------------------------------------------------------------
TRAIN_MEDIANS = {
    "Adult_Dependents": 2.0,
    "Child_Dependents": 0.0,
    "Claim_Rate": 0.0,
    "Claims_to_Duration_Ratio": 0.0,
    "Custom_Riders_Requested": 0.0,
    "Day_Cos": -0.05064916883871264,
    "Day_Sin": -2.4492935982947064e-16,
    "Days_Since_Quote": 49.0,
    "Engagement_Score": 2.0,
    "Estimated_Annual_Income": 34883.31,
    "Existing_Policyholder": 0.0,
    "Grace_Period_Extensions": 1.0,
    "Income_Per_Dependent": 11795.441666666666,
    "Income_to_Deductible_Ratio": 11627.77,
    "Infant_Dependents": 0.0,
    "Is_Returning": 0.0,
    "Log_Income": 10.459792436900951,
    "Loyal_No_Claims": 0.0,
    "Loyalty_Score": 0.0,
    "Month_Cos": 6.123233995736766e-17,
    "Month_Sin": -2.4492935982947064e-16,
    "Policy_Amendments_Count": 0.0,
    "Policy_Cancelled_Post_Purchase": 0.0,
    "Policy_Complexity": 1.0,
    "Policy_Start_Day": 16.0,
    "Policy_Start_Week": 27.0,
    "Policy_Start_Year": 2016.0,
    "Previous_Claims_Filed": 0.0,
    "Previous_Policy_Duration_Months": 2.0,
    "Processing_Delay": 49.0,
    "Risk_Score": 2.0,
    "Total_Dependents": 2.0,
    "Underwriting_Processing_Days": 0.0,
    "Vehicles_on_Policy": 0.0,
    "Week_Cos": -0.23931566428755774,
    "Week_Sin": -3.216245299353273e-16,
    "Years_Without_Claims": 0.0,
}

# Ordinal mapping for Deductible_Tier (treat as ordered numeric)
DEDUCTIBLE_ORDINAL = {
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
    "Low": 1, "Medium": 2, "High": 3,
    "Tier1": 1, "Tier2": 2, "Tier3": 3, "Tier4": 4, "Tier5": 5,
    "unknown": 0, "MISSING": 0,
}


def preprocess(df):
    """
    Judge calls this FIRST on the raw test DataFrame.
    Returns a preprocessed DataFrame that STILL contains User_ID
    (predict needs it for the final output).
    """
    df = df.copy()

    # -------------------------
    # FILL NUMERIC NaNs EARLY  (hardcoded training medians, memory-safe)
    # -------------------------
    num_cols = df.select_dtypes(include=["int64", "float64"]).columns
    for col in num_cols:
        if col in TRAIN_MEDIANS:
            df[col] = df[col].fillna(TRAIN_MEDIANS[col])
        else:
            df[col] = df[col].fillna(0)

    # -------------------------
    # HANDLE MISSING CATEGORICAL  (use 'MISSING' string — preserves info)
    # -------------------------
    cat_cols = [
        "Region_Code", "Broker_Agency_Type",
        "Acquisition_Channel", "Payment_Schedule",
        "Employment_Status", "Policy_Start_Month",
    ]
    for c in cat_cols:
        if c in df.columns:
            df[c] = df[c].fillna("MISSING").astype(str)

    # -------------------------
    # DEDUCTIBLE_TIER: ordinal numeric (ordered cost levels)
    # -------------------------
    if "Deductible_Tier" in df.columns:
        tier_str = df["Deductible_Tier"].fillna("MISSING").astype(str)
        df["Deductible_Tier_Ordinal"] = tier_str.map(DEDUCTIBLE_ORDINAL).fillna(0).astype("float32")
        # Keep original as string category for CatBoost too
        df["Deductible_Tier"] = tier_str

    # -------------------------
    # DROP only Broker_ID & Employer_ID  (keep User_ID!)
    # -------------------------
    for col in ["Broker_ID", "Employer_ID"]:
        if col in df.columns:
            df = df.drop(columns=col)

    # -------------------------
    # CAP EXTREMES
    # -------------------------
    if "Adult_Dependents" in df.columns:
        df["Adult_Dependents"] = np.minimum(df["Adult_Dependents"], 10)
    if "Infant_Dependents" in df.columns:
        df["Infant_Dependents"] = np.minimum(df["Infant_Dependents"], 5)

    # -------------------------
    # INCOME TRANSFORM
    # -------------------------
    if "Estimated_Annual_Income" in df.columns:
        df["Log_Income"] = np.log1p(df["Estimated_Annual_Income"])

    # -------------------------
    # CYCLICAL ENCODING
    # -------------------------
    months = {
        "December": 12, "November": 11, "October": 10,
        "September": 9, "August": 8, "July": 7,
        "June": 6, "May": 5, "April": 4,
        "March": 3, "February": 2, "January": 1,
    }
    if "Policy_Start_Month" in df.columns:
        month_num = df["Policy_Start_Month"].map(months).fillna(6.5)
        df["Month_Sin"] = np.sin(2 * np.pi * month_num / 12)
        df["Month_Cos"] = np.cos(2 * np.pi * month_num / 12)

    if "Policy_Start_Week" in df.columns:
        df["Week_Sin"] = np.sin(2 * np.pi * df["Policy_Start_Week"] / 52)
        df["Week_Cos"] = np.cos(2 * np.pi * df["Policy_Start_Week"] / 52)

    if "Policy_Start_Day" in df.columns:
        df["Day_Sin"] = np.sin(2 * np.pi * df["Policy_Start_Day"] / 31)
        df["Day_Cos"] = np.cos(2 * np.pi * df["Policy_Start_Day"] / 31)

    # -------------------------
    # FEATURE ENGINEERING  (all division-safe)
    # -------------------------
    df["Total_Dependents"] = (
        df.get("Adult_Dependents", 0)
        + df.get("Child_Dependents", 0)
        + df.get("Infant_Dependents", 0)
    )

    df["Claim_Rate"] = (
        df.get("Previous_Claims_Filed", 0)
        / (df.get("Years_Without_Claims", 0) + 1)
    )

    df["Policy_Complexity"] = (
        df.get("Vehicles_on_Policy", 0)
        + df.get("Custom_Riders_Requested", 0)
        + df.get("Policy_Amendments_Count", 0)
    )

    df["Processing_Delay"] = (
        df.get("Underwriting_Processing_Days", 0)
        + df.get("Days_Since_Quote", 0)
    )

    # STRENGTHENED Risk_Score: heavier weights on cancellations & grace periods
    df["Risk_Score"] = (
        df.get("Previous_Claims_Filed", 0) * 2
        - df.get("Years_Without_Claims", 0)
        + df.get("Policy_Cancelled_Post_Purchase", 0) * 5   # was 3
        + df.get("Grace_Period_Extensions", 0) * 2          # was 1
    )

    df["Income_Per_Dependent"] = (
        df.get("Estimated_Annual_Income", 0) / (df["Total_Dependents"] + 1)
    )

    df["Engagement_Score"] = (
        df.get("Policy_Amendments_Count", 0)
        + df.get("Grace_Period_Extensions", 0)
        + df.get("Custom_Riders_Requested", 0)
    )

    if "Existing_Policyholder" in df.columns:
        df["Is_Returning"] = df["Existing_Policyholder"].astype(int)
    else:
        df["Is_Returning"] = 0

    df["Loyalty_Score"] = (
        df.get("Years_Without_Claims", 0)
        * df.get("Previous_Policy_Duration_Months", 0)
    )

    if "Existing_Policyholder" in df.columns and "Years_Without_Claims" in df.columns:
        df["Loyal_No_Claims"] = (
            (df["Existing_Policyholder"] == 1) & (df["Years_Without_Claims"] > 3)
        ).astype(int)
    else:
        df["Loyal_No_Claims"] = 0

    # -------------------------
    # NEW INTERACTION FEATURES
    # -------------------------
    # Income relative to deductible burden
    deductible_ord = df.get("Deductible_Tier_Ordinal", None)
    if deductible_ord is not None:
        df["Income_to_Deductible_Ratio"] = (
            df.get("Estimated_Annual_Income", 0) / (deductible_ord + 1)
        )
    else:
        df["Income_to_Deductible_Ratio"] = df.get("Estimated_Annual_Income", 0)

    # Claims frequency relative to policy duration
    df["Claims_to_Duration_Ratio"] = (
        df.get("Previous_Claims_Filed", 0)
        / (df.get("Previous_Policy_Duration_Months", 0) + 1)
    )

    # -------------------------
    # FINAL NUMERIC NaN SWEEP  (catches NaN from engineered features)
    # -------------------------
    num_cols = df.select_dtypes(include=["int64", "float64"]).columns
    for col in num_cols:
        if col in TRAIN_MEDIANS:
            df[col] = df[col].fillna(TRAIN_MEDIANS[col])
        else:
            df[col] = df[col].fillna(0)

    # -------------------------
    # MEMORY OPTIMISATION: downcast float64 → float32
    # -------------------------
    float64_cols = df.select_dtypes(include=["float64"]).columns
    df[float64_cols] = df[float64_cols].astype("float32")

    return df


def load_model():
    """Load the trained CatBoost model from disk (joblib .pkl)."""
    model_path = "model.pkl"
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    return joblib.load(model_path)


def predict(df, model):
    """
    Judge calls this with the ALREADY-PREPROCESSED DataFrame from preprocess().
    Do NOT call preprocess() again here.

    Returns a DataFrame with exactly:  User_ID | Purchased_Coverage_Bundle
    """
    n_input = len(df)

    # ---- Extract User_IDs (preprocess kept them) ----
    user_ids = df["User_ID"].values

    # ---- Drop User_ID before feeding to the model ----
    df_model = df.drop(columns=["User_ID"], errors="ignore")

    # ---- Inference ----
    preds = model.predict(df_model)

    # CatBoost may return a 2-D array (n, 1) — flatten to 1-D
    if hasattr(preds, "ndim") and preds.ndim > 1:
        preds = preds.ravel()

    # ---- Cast predictions to int (judge expects integer labels) ----
    preds = np.asarray(preds, dtype=int)

    # ---- Build judge-required output ----
    result = pd.DataFrame({
        "User_ID": user_ids,
        "Purchased_Coverage_Bundle": preds,
    })

    assert len(result) == n_input, (
        f"Row count mismatch: input={n_input}, output={len(result)}"
    )

    return result


if __name__ == "__main__":
    # ---- Local sanity check mimicking the judge pipeline ----
    df = pd.read_csv("test.csv")

    # Step 1: preprocess  (judge does this)
    df_processed = preprocess(df)

    # Step 2: load model  (judge does this)
    model = load_model()

    # Step 3: predict     (judge does this)
    output = predict(df_processed, model)

    print("Output shape :", output.shape)
    print("Output columns:", list(output.columns))
    print("Output dtypes:")
    print(output.dtypes)
    print(output.head(10))

    # Validate judge requirements
    assert list(output.columns) == ["User_ID", "Purchased_Coverage_Bundle"], \
        "Column mismatch!"
    assert output.shape[0] == df.shape[0], \
        f"Row count mismatch: expected {df.shape[0]}, got {output.shape[0]}"
    assert output["Purchased_Coverage_Bundle"].dtype in [np.int32, np.int64, int], \
        f"Predictions must be int, got {output['Purchased_Coverage_Bundle'].dtype}"
    print("\n✅ All checks passed — output is judge-ready.")
