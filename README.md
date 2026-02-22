#  Team-3ami — DataQuest Hackathon

> An end-to-end ML classification solution with an interactive web interface, MLOps pipeline, and Explainable AI insights.

---

##  Team Members

- Hashem Ghorbel  
- Mohamed Abdelhedi
- Faouzi Blibech       
- Ahmed Aziz Hasnaoui

---

##  Project Overview

This project was built for the **DataQuest Hackathon**. It tackles a classification problem using a **CatBoost** model, served through a **Flask** web application with a clean **HTML/CSS** frontend. The solution is designed with **MLOps** best practices and includes a dedicated **Explainable AI (XAI)** module to make model predictions interpretable and transparent.

---

##  Features

-  **CatBoost Classification** — High-performance gradient boosting model optimized for categorical features
-  **Flask Web App** — Lightweight Python backend serving predictions via REST endpoints
-  **HTML/CSS Frontend** — Clean and responsive user interface for submitting inputs and viewing results
-  **Explainable AI (XAI)** — SHAP-based explanations to interpret model predictions at both global and local levels
-  **MLOps Pipeline** — Structured training, versioning, and deployment workflow

---

##  Project Structure

```
Team-3ami/
│
├── python_model_service/       # Flask API service for model inference
│
├── train_model.py              # Model training script (CatBoost)
├── solution.py                 # Main solution logic
├── stat.py                     # Statistical analysis utilities
│
├── explainability.ipynb        # XAI notebook (SHAP analysis)
├── model.pkl                   # Serialized trained CatBoost model
│
├── requirements.txt            # Python dependencies
└── README.md
```

---

##  Getting Started

### Prerequisites

- Python 3.10
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/hash-em/Team-3ami.git
cd Team-3ami

# Install Python dependencies
pip install -r requirements.txt

# Install JS dependencies (if applicable)
npm install
```

### Run the Flask App

```bash
python solution.py
```

The app will be available at `http://localhost:5000`.

---

##  Model — CatBoost Classifier

The core ML model is a **CatBoost Classifier**, chosen for its:

- Native support for categorical features (no manual encoding required)
- Strong performance on tabular data with minimal hyperparameter tuning
- Fast training with GPU support
- Built-in handling of missing values

Training is handled in `train_model.py`. The final trained model is serialized to `model.pkl` and loaded by the Flask service at runtime.

---

##  Explainable AI (XAI)

The `explainability.ipynb` notebook provides transparency into the model's decision-making using **SHAP (SHapley Additive exPlanations)**:

- **Global Explainability** — Feature importance across the entire dataset
- **Local Explainability** — Per-prediction explanation showing which features drove a specific output
- **SHAP Summary Plots** — Visual breakdowns of feature contributions
- **Force Plots** — Intuitive visualization for individual predictions

This ensures the model is not a "black box" and that predictions can be audited and trusted.

---

##  MLOps

The project follows MLOps principles to ensure reproducibility and maintainability:

- **Structured training pipeline** via `train_model.py`
- **Model versioning** with serialized `.pkl` artifacts
- **Dedicated model service** (`python_model_service/`) decoupling inference from the main app
- **Dependency pinning** via `requirements.txt`

---

##  Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| ML Model | CatBoost |
| Explainability | SHAP |
| MLOps | Custom pipeline, model serialization |

---

##  License

This project was developed for hackathon purposes. See the repository for more details.

---

*Built with ❤️ by Team-3ami for the DataQuest Hackathon*
