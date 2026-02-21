from numpy._core.umath import NAN
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
import joblib


def preprocess(df):

    df = df.copy()

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
            df[c] = df[c].fillna(NAN)

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
