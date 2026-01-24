from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

# --- State ---
class DirectorState(TypedDict):
    project_id: str
    live_metrics: dict
    audit_plan: dict
    alerts: Optional[list]

# --- Nodes ---
def node_data_fetcher(state: DirectorState):
    """
    Connects to Meta/TikTok APIs (Mock for now).
    """
    print("--- DIRECTOR: FETCHING DATA ---")
    # Mock data
    mock_metrics = {
        "facebook": {"cpc": 1.20, "ctr": 0.8},
        "tiktok": {"cpc": 0.50, "ctr": 1.5}
    }
    return {"live_metrics": mock_metrics}

def node_metric_normalizer(state: DirectorState):
    """
    Normalizes metrics to Meraki Standard.
    """
    print("--- DIRECTOR: NORMALIZING ---")
    raw = state["live_metrics"]
    # Logic to merge fields would go here
    normalized = {
        "blended_cpc": (raw["facebook"]["cpc"] + raw["tiktok"]["cpc"]) / 2,
        "blended_ctr": (raw["facebook"]["ctr"] + raw["tiktok"]["ctr"]) / 2
    }
    return {"live_metrics": normalized} # Overwrite or create new key

def node_auditor(state: DirectorState):
    """
    Compares metrics against benchmarks.
    """
    print("--- DIRECTOR: AUDITING ---")
    metrics = state["live_metrics"]
    alerts = []
    
    if metrics["blended_ctr"] < 1.0:
        alerts.append("Alert: Low CTR. Creative fatigue detected.")
        
    return {"alerts": alerts}

# --- Graph ---
workflow = StateGraph(DirectorState)
workflow.add_node("data_fetcher", node_data_fetcher)
workflow.add_node("normalizer", node_metric_normalizer)
workflow.add_node("auditor", node_auditor)

workflow.set_entry_point("data_fetcher")
workflow.add_edge("data_fetcher", "normalizer")
workflow.add_edge("normalizer", "auditor")
workflow.add_edge("auditor", END)

director_app = workflow.compile()
