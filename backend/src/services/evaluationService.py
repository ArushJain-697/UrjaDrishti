# Person 4 hook is now live.
# get_results() currently returns shaped mock data (Day 1).
# On Day 3, the TODO inside get_results() will be completed
# once Person 2's forecast DataFrame is available.
from src.ml.evaluation.metrics import get_results as ml_results

def get_evaluation():
    try:
        return ml_results()
    except Exception as e:
        print(f"Evaluation error: {e}")
        raise