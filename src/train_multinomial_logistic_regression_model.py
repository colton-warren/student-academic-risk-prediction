import mlflow
import numpy as np
import os
import pandas as pd
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler

# Create data
data = pd.read_csv("data/processed/cleaned_student_data.csv")
X = data.drop(columns=["target"])
y = data["target"]
print("Data Load Successful") 

# Split the data into training and validation sets
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

# Scale data
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
feature_params = {"preprocessing": "StandardScaler"}

# Train a Multinomial Linear Regression model
model = LogisticRegression(multi_class="multinomial", solver="lbfgs", max_iter=1000, random_state=42)
model.fit(X_train_scaled, y_train)

# Evaluate the model
y_pred = model.predict(X_val_scaled)

# Set MLflow experiment name
mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("Student Academic Risk Prediction")

# Log experiment details
with mlflow.start_run(run_name="Multinomial Linear Regression Model"):
	
	# Log hyperparameters to MLFlow
	mlflow.log_param("model_type", "Multinomial Logistic Regression")
	mlflow.log_param("multi_class", "multinomial")
	mlflow.log_param("solver", "lbfgs")
	mlflow.log_param("max_iter", 1000)
	mlflow.log_params(feature_params)
	mlflow.sklearn.log_model(model, artifact_path="model")

	# Calculate performance metrics
	accuracy = accuracy_score(y_val, y_pred)
	precision_macro = precision_score(y_val, y_pred, average="macro", zero_division=0)
	recall_macro = 	recall_score(y_val, y_pred, average="macro", zero_division=0)
	f1_macro = f1_score(y_val, y_pred, average="macro", zero_division=0) 

	# Calculate recall for drop out
	dropout_recall = recall_score(y_val, y_pred, labels=["Dropout"], average="micro", zero_division=0) 

	# Log performance metrics to MLflow
	mlflow.log_metric("accuracy", accuracy)
	mlflow.log_metric("precision_macro", precision_macro)
	mlflow.log_metric("recall_macro", recall_macro)
	mlflow.log_metric("f1_macro", f1_macro)
	mlflow.log_metric("recall_dropout", dropout_recall)

	# Register model programmatically
	active_run = mlflow.active_run().info.run_id
	model_uri = f"runs:/{active_run}/model"
	registered_model = mlflow.register_model(model_uri=model_uri, name="Multinomial Linear Regression Model")

	# Add metadata: Tags and Aliases
	client = mlflow.tracking.MlflowClient()
	client.set_registered_model_tag(
		registered_model.name, "validation_status", "pending"
	)
	client.set_registered_model_alias(
		registered_model.name, "challenger", version=registered_model.version
	)