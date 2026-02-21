from numpy._core.umath import NAN
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
import joblib


def preprocess(df):

    df = df.copy()
    # Cyclical encoding for month/week/day (captures periodicity)
    df["Month_Sin"] = np.sin(2 * np.pi * df["Policy_Start_Month"] / 12)
    df["Month_Cos"] = np.cos(2 * np.pi * df["Policy_Start_Month"] / 12)
    df["Week_Sin"] = np.sin(2 * np.pi * df["Policy_Start_Week"] / 52)
    df["Week_Cos"] = np.cos(2 * np.pi * df["Policy_Start_Week"] / 52)
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
    return df

def load_model():
    # Load and return your trained model from disk.
    # Example: return joblib.load('model.pkl')
    model = None
    return model

def predict(df, model):
    # Generate predictions on the preprocessed DataFrame.
    # This is the only function that is timed.
    predictions = None
    return predictions
if __name__ == '__main__':
    df = pd.read_csv('test.csv')
    preprocess(df)
