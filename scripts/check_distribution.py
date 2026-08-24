import pandas as pd
from ai.features.engineer import build_features, ACTION_TYPES
from ai.inference import predict
from domain.recovery.ranking import rank_candidate_actions

def check_distribution():
    predict.load_models()
    df = pd.read_csv("data/processed/test.csv")
    
    top_actions = []
    
    for _, row in df.iterrows():
        case_context = {
            "amount_paise": row.get("amount_paise", 100000),
            "failure_type": row.get("failure_type", "TEMPORARY"),
            "segment": row.get("segment", "MEDIUM_VALUE"),
            "tenure_days": row.get("tenure_days", 30),
            "high_frequency_contact": row.get("high_frequency_contact", False),
            "requires_human_review": row.get("requires_human_review", False)
        }
        
        df_single = pd.DataFrame([case_context])
        X_base = build_features(df_single)
        
        action_probs = {}
        for a in ACTION_TYPES:
            X_action = X_base.copy()
            for act in ACTION_TYPES:
                X_action[f"action_{act}"] = 1 if act == a else 0
            prob = float(predict._intervention_model.predict_proba(X_action)[0, 1])
            action_probs[a] = prob
            
        ranked = rank_candidate_actions(case_context["amount_paise"], action_probs)
        top_actions.append(ranked[0].action_type)
        
    dist = pd.Series(top_actions).value_counts()
    print("Top Action Distribution in Test Set:")
    print(dist)

if __name__ == "__main__":
    check_distribution()
