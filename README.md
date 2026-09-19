# student-academic-risk-prediction
Group 7 Student Academic Risk Prediction MVP

To reproduce this environment on you harddrive

```git clone https://github.com/colton-warren/student-academic-risk-prediction.git
cd student-academic-risk-prediction
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
dvc pull
python src/train.py
```