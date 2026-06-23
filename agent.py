import os
from typing import TypedDict
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langgraph.graph import StateGraph, END

# 1. Unlock the Vault
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("CRITICAL: GEMINI_API_KEY not found.")

# 2. Connect to the Chroma Brain
print("Connecting to Vector Database...")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
vector_db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
retriever = vector_db.as_retriever(search_kwargs={"k": 3})

# 3. Initialize the Core LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# 4. Define the State
class AgentState(TypedDict):
    user_message: str
    intent: str
    technical_context: str
    final_answer: str

# ---------------------------------------------------------
# THE CLASSIFIER CASCADE (Zero-Cost Optimization)
# ---------------------------------------------------------
def route_intent(state: AgentState):
    print("--- NODE: ROUTER (CASCADE ENGINE) ---")
    message = state["user_message"].lower()
    
    # LEVEL 1: Zero-Cost Heuristic Pre-filter
    # We check for obvious technical keywords. If matched, we route immediately.
    # Cost: 0 tokens. Latency: < 1ms.
    tech_keywords = [
        "specification", "hydraulic", "viscosity", "torque", 
        "manual", "pressure", "voltage", "machine", "cooker", "capacity"
    ]
    
    if any(kw in message for kw in tech_keywords):
        print("Status: TECHNICAL (Intercepted by Level 1 Heuristic - 0 Tokens Burned)")
        return {"intent": "TECHNICAL"}

    # LEVEL 2: LLM Evaluation 
    # Only wakes up the API for ambiguous, nuanced queries.
    print("Status: Ambiguous query detected. Waking up LLM for classification...")
    prompt = f"""You are the DocuRoute AI intent router. 
    Output exactly the word 'TECHNICAL' if the user asks about machinery, metrics, or operations. 
    Otherwise, output exactly the word 'GENERAL'.
    User Message: {message}"""
    
    response = llm.invoke(prompt).content.strip().upper()
    
    # LEVEL 3: Defensive Guardrail
    # If the LLM hallucinates extra punctuation or weird capitalization, we catch it safely.
    if "TECHNICAL" in response:
        print("Status: TECHNICAL (Determined by LLM)")
        return {"intent": "TECHNICAL"}
    
    print("Status: GENERAL (Determined by LLM Fallback)")
    return {"intent": "GENERAL"}

# ---------------------------------------------------------
# THE WORKERS (NODES)
# ---------------------------------------------------------
def retrieve_specs(state: AgentState):
    print("--- NODE: RAG ENGINEER ---")
    message = state["user_message"]
    docs = retriever.invoke(message)
    context = "\n\n".join([doc.page_content for doc in docs])
    print(f"Retrieved {len(docs)} chunks of technical data.")
    return {"technical_context": context}

def general_chat(state: AgentState):
    print("--- NODE: GENERAL RECEPTIONIST ---")
    return {"technical_context": "No technical context needed."}

def generate_answer(state: AgentState):
    print("--- NODE: FORMATTER ---")
    intent = state["intent"]
    context = state.get("technical_context", "")
    message = state["user_message"]
    
    if intent == "TECHNICAL":
        prompt = f"""You are a senior technical sales engineer for DocuRoute AI. 
        Answer the user's question using ONLY the following context. 
        If the context does not contain the answer, do not guess. Say you need to consult the engineering team.
        
        Context: {context}
        Question: {message}"""
    else:
        prompt = f"""You are a helpful representative for DocuRoute AI. 
        Respond politely and professionally to this message: {message}"""
        
    response = llm.invoke(prompt)
    return {"final_answer": response.content}

# ---------------------------------------------------------
# THE TRAFFIC LIGHTS (EDGES)
# ---------------------------------------------------------
def route_to_next(state: AgentState):
    if state["intent"] == "TECHNICAL":
        return "retrieve_specs"
    return "general_chat"

# ---------------------------------------------------------
# COMPILE THE SYSTEM
# ---------------------------------------------------------
print("Compiling LangGraph Engine...")
workflow = StateGraph(AgentState)

workflow.add_node("route_intent", route_intent)
workflow.add_node("retrieve_specs", retrieve_specs)
workflow.add_node("general_chat", general_chat)
workflow.add_node("generate_answer", generate_answer)

workflow.set_entry_point("route_intent")
workflow.add_conditional_edges("route_intent", route_to_next)

workflow.add_edge("retrieve_specs", "generate_answer")
workflow.add_edge("general_chat", "generate_answer")
workflow.add_edge("generate_answer", END)

app = workflow.compile()

# ---------------------------------------------------------
# LOCAL TESTING TERMINAL
# ---------------------------------------------------------
if __name__ == "__main__":
    print("\n=== DOCUROUTE ENTERPRISE ENGINE ONLINE ===\n")
    
    # Test 1: Should be caught by Level 1 (Zero Cost)
    test_message_1 = "What is the voltage of the Industrial Steam Cooker?"
    print(f"USER: {test_message_1}")
    result_1 = app.invoke({"user_message": test_message_1})
    print(f"\nFINAL OUTPUT:\n{result_1['final_answer']}\n")
    print("-" * 50)
    
    # Test 2: Should bypass Level 1 and trigger Level 2 (LLM Route)
    test_message_2 = "Hi, I am looking to buy some machines."
    print(f"USER: {test_message_2}")
    result_2 = app.invoke({"user_message": test_message_2})
    print(f"\nFINAL OUTPUT:\n{result_2['final_answer']}\n")