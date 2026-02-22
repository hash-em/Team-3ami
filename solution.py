from numpy._core.umath import NAN
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
import joblib


def preprocess(df):

    df = df.copy()
    # Cyclical encoding for month/week/day (captures periodicity)
    months = {
        "December": 12,
        "November": 11,
        "October": 10,
        "September": 9,
        "August": 8,
        "July": 7,
        "June": 6,
        "May": 5,
        "April": 4,
        "March": 3,
        "February": 2,
        "January": 1
    }
    if "Policy_Start_Month" in df.columns:
        month_num = df["Policy_Start_Month"].map(months)
        month_num = month_num.fillna(6.5)   # safe fallback

        df["Month_Sin"] = np.sin(2 * np.pi * month_num / 12)
        df["Month_Cos"] = np.cos(2 * np.pi * month_num / 12)

    # ---- Week (already numeric 1–52)
    if "Policy_Start_Week" in df.columns:
        df["Week_Sin"] = np.sin(2 * np.pi * df["Policy_Start_Week"] / 52)
        df["Week_Cos"] = np.cos(2 * np.pi * df["Policy_Start_Week"] / 52)

    # ---- Day (already numeric 1–31)
    if "Policy_Start_Day" in df.columns:
        df["Day_Sin"] = np.sin(2 * np.pi * df["Policy_Start_Day"] / 31)
        df["Day_Cos"] = np.cos(2 * np.pi * df["Policy_Start_Day"] / 31)
    # -------------------------
    # DROP IDS
    # -------------------------
    for col in ["User_ID","Broker_ID","Employer_ID"]:
        if col in df.columns:
            df = df.drop(columns=col)

    # -------------------------
    # HANDLE MISSING CATEGORICAL
    # -------------------------
    cat_cols = [
        "Region_Code",
        "Broker_Agency_Type",
        "Deductible_Tier",
        "Acquisition_Channel",
        "Payment_Schedule",
        "Employment_Status",
        "Policy_Start_Month"
    ]

    for c in cat_cols:
        if c in df.columns:
            df[c] = df[c].fillna("unknown")

    # -------------------------
    # CAP EXTREMES
    # -------------------------
    df["Adult_Dependents"] = np.minimum(df["Adult_Dependents"], 10)
    df["Infant_Dependents"] = np.minimum(df["Infant_Dependents"], 5)

    # -------------------------
    # INCOME TRANSFORM
    # -------------------------
    if "Estimated_Annual_Income" in df.columns:
        df["Log_Income"] = np.log1p(df["Estimated_Annual_Income"])

    # -------------------------
    # FEATURE ENGINEERING
    # -------------------------
    df["Total_Dependents"] = (
        df["Adult_Dependents"]
        + df["Child_Dependents"]
        + df["Infant_Dependents"]
    )

    df["Claim_Rate"] = (
        df["Previous_Claims_Filed"]
        / (df["Years_Without_Claims"] + 1)
    )

    df["Policy_Complexity"] = (
        df["Vehicles_on_Policy"]
        + df["Custom_Riders_Requested"]
        + df["Policy_Amendments_Count"]
    )

    df["Processing_Delay"] = (
        df["Underwriting_Processing_Days"]
        + df["Days_Since_Quote"]
    )
    # Risk score
    df["Risk_Score"] = (
        df["Previous_Claims_Filed"] * 2
        - df["Years_Without_Claims"]
        + df["Policy_Cancelled_Post_Purchase"] * 3
        + df["Grace_Period_Extensions"]
    )

    # Income per dependent (purchasing power)
    df["Income_Per_Dependent"] = df["Estimated_Annual_Income"] / (df["Total_Dependents"] + 1)

    # Engagement score (how involved the customer is)
    df["Engagement_Score"] = (
        df["Policy_Amendments_Count"]
        + df["Grace_Period_Extensions"]
        + df["Custom_Riders_Requested"]
    )

    # Is a returning customer?
    df["Is_Returning"] = df["Existing_Policyholder"].astype(int)

    # Long-term loyalty proxy
    df["Loyalty_Score"] = df["Years_Without_Claims"] * df["Previous_Policy_Duration_Months"]
    # Existing customers with no claims are very different from new ones
    df["Loyal_No_Claims"] = (
        (df["Existing_Policyholder"] == 1) & (df["Years_Without_Claims"] > 3)
    ).astype(int)

    df = df.drop_duplicates()
    num_cols = df.select_dtypes(include=["int64","float64"]).columns
    df[num_cols] = df[num_cols].fillna(df[num_cols].median())

    return df

def load_model():
    """Load the trained CatBoost model from disk."""
    model = CatBoostClassifier()
    model.load_model("model.cbm")
    return model


def predict(df, model):
    """
    Generate predictions and return a DataFrame with exactly:
        User_ID  |  Purchased_Coverage_Bundle
    """
    # ---- preserve User_IDs BEFORE preprocess drops them ----
    user_ids = df["User_ID"].copy()

    # ---- run the teammate's preprocess (untouched) ----
    df_processed = preprocess(df)

    # ---- inference ----
    preds = model.predict(df_processed)

    # CatBoost may return a 2-D array (n, 1) — flatten to 1-D
    if hasattr(preds, "ndim") and preds.ndim > 1:
        preds = preds.ravel()

    # ---- build judge-required output ----
    result = pd.DataFrame({
        "User_ID": user_ids,
        "Purchased_Coverage_Bundle": preds,
    })

    return result


if __name__ == "__main__":
    # ---- quick local sanity check ----
    df = pd.read_csv("test.csv")
    model = load_model()
    output = predict(df, model)

    print("Output shape :", output.shape)
    print("Output columns:", list(output.columns))
    print(output.head(10))

    # Validate judge requirements
    assert list(output.columns) == ["User_ID", "Purchased_Coverage_Bundle"], \
        "Column mismatch!"
    assert output.shape[0] == df.shape[0], \
        f"Row count mismatch: expected {df.shape[0]}, got {output.shape[0]}"
    print("\n✅ All checks passed — output is judge-ready.")
