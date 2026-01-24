from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
import json

class BlueprintState(TypedDict):
    genesis_report: dict
    funnel_structure: Optional[dict]

llm = ChatOpenAI(model="gpt-4o", temperature=0)

def node_architect(state: BlueprintState):
    """
    Decides the funnel strategy based on the Genesis Report.
    """
    print("--- BLUEPRINT ARCHITECT ---")
    report = state["genesis_report"]
    awareness = report.get("awareness_level", "Unknown")
    
    prompt = f"""
    You are the Architect Agent of MerakiOS.
    Based on the Market Awareness Level: '{awareness}', design the optimal funnel.
    
    Logic:
    - Unaware/Problem Aware -> Education Funnel (Ad -> VSL/Blog -> Optin).
    - Solution Aware/Product Aware -> Direct Offer Funnel (Ad -> Sales Page -> Checkout).
    
    Return a React Flow compatible JSON structure with 'nodes' and 'edges'.
    Nodes must have: id, type (ad_node, landing_page, email_seq, checkout), label, position.
    Edges must have: id, source, target.
    
    Example Schema:
    {{
      "nodes": [{{ "id": "1", "type": "ad_node", "label": "Hook Ad", "position": {{ "x": 0, "y": 0 }} }}],
      "edges": []
    }}
    """
    
    response = llm.invoke(prompt)
    try:
        blueprint = json.loads(response.content)
    except:
        blueprint = {"nodes": [], "edges": [], "error": "Failed to parse blueprint"}
        
    return {"funnel_structure": blueprint}

def node_content_router(state: BlueprintState):
    """
    (Placeholder for Phase 2)
    Would analyze nodes and decide which specialist agent is needed (Copywriter vs Prompt Engineer).
    For MVP, we just pass through.
    """
    print("--- BLUEPRINT ROUTER ---")
    return {}

workflow = StateGraph(BlueprintState)
workflow.add_node("node_architect", node_architect)
workflow.add_node("node_content_router", node_content_router)

workflow.set_entry_point("node_architect")
workflow.add_edge("node_architect", "node_content_router")
workflow.add_edge("node_content_router", END)

blueprint_app = workflow.compile()
