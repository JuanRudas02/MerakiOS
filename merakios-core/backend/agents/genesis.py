from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json

# --- State Definition ---
class GenesisState(TypedDict):
    niche: str
    url: Optional[str]
    search_queries: Optional[List[str]]
    search_results: Optional[List[str]]
    audit_report: Optional[dict]
    missing_info: Optional[bool]
    loop_count: int

# --- Setup ---
llm = ChatOpenAI(model="gpt-4o", temperature=0)
search_tool = TavilySearchResults(max_results=3)

# --- Nodes ---

def node_planner(state: GenesisState):
    """
    Analyzes the initial request and generates search queries.
    """
    print("--- GENESIS PLANNER ---")
    niche = state["niche"]
    
    prompt = f"""
    You are a Strategic Planner for MerakiOS.
    Goal: We need to audit the market for: {niche}.
    
    Generate 3 specific search queries to find:
    1. Pain points & desires.
    2. Competitor offers.
    3. Market awareness level.
    
    Return ONLY a JSON list of strings: ["query 1", "query 2", "query 3"]
    """
    response = llm.invoke(prompt)
    try:
        queries = json.loads(response.content)
        # Ensure it's a list
        if not isinstance(queries, list): queries = [queries]
    except:
        queries = [f"{niche} pain points", f"{niche} competitors", f"{niche} forums"]
        
    return {"search_queries": queries, "loop_count": state.get("loop_count", 0)}

def node_researcher(state: GenesisState):
    """
    Executes search queries using Tavily.
    """
    print("--- GENESIS RESEARCHER ---")
    queries = state["search_queries"]
    results_acc = state.get("search_results", []) or []
    
    for q in queries:
        try:
            res = search_tool.invoke(q)
            results_acc.append(f"Query: {q}\nResult: {str(res)}")
        except Exception as e:
            print(f"Search error: {e}")
            
    return {"search_results": results_acc}

def node_auditor(state: GenesisState):
    """
    Analyzes data using marketing frameworks (Schwartz, JTBD).
    Checks if info is sufficient.
    """
    print("--- GENESIS AUDITOR ---")
    results = "\n\n".join(state["search_results"])
    niche = state["niche"]
    
    prompt = f"""
    You are the Senior Auditor Agent of MerakiOS.
    Analyze these search results for the niche '{niche}':
    {results}
    
    Your task is to populate the Meraki Strategy JSON.
    
    Frameworks to apply:
    1. Eugene Schwartz Awareness Levels (Unaware -> Most Aware).
    2. Jobs To Be Done (What is the user really trying to achieve?).
    
    If the data is insufficient to determine the Avatar or Pain Points, set "missing_info": true.
    Otherwise, set "missing_info": false and provide the full report.
    
    Return a valid JSON:
    {{
      "missing_info": boolean,
      "report": {{
        "avatar": "Description...",
        "pain_points": ["..."],
        "awareness_level": "...",
        "market_opportunity": "..."
      }}
    }}
    """
    
    response = llm.invoke([SystemMessage(content="Return strictly valid JSON."), HumanMessage(content=prompt)])
    try:
        analysis = json.loads(response.content)
    except:
        analysis = {"missing_info": False, "report": {"error": "JSON parse error"}}
        
    return {
        "audit_report": analysis.get("report"),
        "missing_info": analysis.get("missing_info", False),
        "loop_count": state["loop_count"] + 1
    }

# --- Conditional Edge ---
def check_completeness(state: GenesisState):
    if state.get("missing_info") and state["loop_count"] < 2:
        return "node_planner" # Loop back to get better queries
    return "end"

# --- Graph ---
workflow = StateGraph(GenesisState)

workflow.add_node("node_planner", node_planner)
workflow.add_node("node_researcher", node_researcher)
workflow.add_node("node_auditor", node_auditor)

workflow.set_entry_point("node_planner")
workflow.add_edge("node_planner", "node_researcher")
workflow.add_edge("node_researcher", "node_auditor")

workflow.add_conditional_edges(
    "node_auditor",
    check_completeness,
    {
        "node_planner": "node_planner",
        "end": END
    }
)

genesis_app = workflow.compile()
