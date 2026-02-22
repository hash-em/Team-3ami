"""Compute training-set medians for hardcoding into preprocess()."""
import pandas as pd
import numpy as np
from solution import preprocess

df = pd.read_csv("train.csv")
target = df["Purchased_Coverage_Bundle"]
df = df.drop(columns=["Purchased_Coverage_Bundle"])
df_p = preprocess(df)

num_cols = df_p.select_dtypes(include=["int64", "float64"]).columns
medians = df_p[num_cols].median()

print("TRAIN_MEDIANS = {")
for k, v in sorted(medians.items()):
    print(f'    "{k}": {v},')
print("}")
