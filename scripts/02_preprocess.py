"""
Loads sugarcane_data.csv, handles missing values, encodes categoricals,
scales numerical features. Outputs a model-ready DataFrame.
Run: python 02_preprocess.py
"""
import pandas as pd
from sklearn.preprocessing import StandardScaler

df = pd.read_csv("../data/sugarcane_data.csv")

TARGETS = ["bagasse_tons", "leaves_tons", "press_mud_tons"]
CATEGORICAL = ["sugarcane_variety", "soil_type", "irrigation_type"]
NUMERICAL = ["crop_age_months", "farm_acreage", "rainfall_mm", "fertilizer_kg_per_acre"]

# 1. Handle missing values
df[NUMERICAL] = df[NUMERICAL].fillna(df[NUMERICAL].median())
df["soil_type"] = df["soil_type"].fillna(df["soil_type"].mode()[0])

# 2. Encode categoricals (one-hot)
df_encoded = pd.get_dummies(df, columns=CATEGORICAL, drop_first=True)

# 3. Scale numerical features
scaler = StandardScaler()
df_encoded[NUMERICAL] = scaler.fit_transform(df_encoded[NUMERICAL])

# Final feature/target split
X = df_encoded.drop(columns=TARGETS + ["farm_id"])
y = df_encoded[TARGETS]

df_encoded.to_csv("../data/sugarcane_data_processed.csv", index=False)
print("Processed shape:", df_encoded.shape)
print("Feature columns:", list(X.columns))
