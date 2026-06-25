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
# THE CLASSIFIER CASCADE
# ---------------------------------------------------------
def route_intent(state: AgentState):
    print("--- NODE: ROUTER (CASCADE ENGINE) ---")
    message = state["user_message"].lower().strip()

    # LEVEL 0: Conversational intercept (greetings / filler) — route GENERAL, 0 tokens.
    # Whole-word match so "hi" doesn't fire inside "high-pressure".
    words = set(message.replace("?", "").replace(".", "").replace(",", "").split())
    greetings = {"hi", "hello", "hey", "thanks", "thank", "bye", "ok", "okay"}
    if words & greetings and len(words) <= 5:
        print("Status: GENERAL (Level 0 conversational intercept - 0 tokens)")
        return {"intent": "GENERAL"}

    # LEVEL 1: Technical keyword heuristic — whole-word match, 0 tokens.
    tech_keywords = {
        "specification", "specifications", "hydraulic", "viscosity", "torque",
        "manual", "pressure", "voltage", "machine", "machines", "cooker",
        "capacity", "kilowatts", "kw", "power", "heater", "heaters"
    }
    if words & tech_keywords:
        print("Status: TECHNICAL (Level 1 heuristic - 0 tokens)")
        return {"intent": "TECHNICAL"}

    # LEVEL 2: LLM evaluation for ambiguous queries.
    print("Status: Ambiguous - invoking LLM classifier...")
    prompt = f"""You are the DocuRoute AI intent router.
Output exactly the word 'TECHNICAL' if the user asks about machinery, metrics, specs, or operations.
Otherwise output exactly the word 'GENERAL'.
User Message: {message}"""
    response = llm.invoke(prompt).content.strip().upper()

    if "TECHNICAL" in response:
        print("Status: TECHNICAL (LLM)")
        return {"intent": "TECHNICAL"}
    print("Status: GENERAL (LLM)")
    return {"intent": "GENERAL"}

# ---------------------------------------------------------
# THE WORKERS (NODES)
# ---------------------------------------------------------
def retrieve_specs(state: AgentState):
    print("--- NODE: RAG ENGINEER ---")
    docs = retriever.invoke(state["user_message"])
    context = "\n\n".join([doc.page_content for doc in docs])
    print(f"Retrieved {len(docs)} chunks of technical data.")
    return {"technical_context": context}

def general_chat(state: AgentState):
    print("--- NODE: GENERAL RECEPTIONIST ---")
    return {"technical_context": "No technical context needed."}

def generate_answer(state: AgentState):
    print("--- NODE: FORMATTER ---")
    intent = state["intent"]
    message = state["user_message"]

    if intent == "TECHNICAL":
        context = state.get("technical_context", "")
        prompt = f"""You are a senior technical sales engineer for DocuRoute AI.
Answer using ONLY the following context. If the context lacks the answer,
do not guess — say you need to consult the engineering team.

Context: {context}
Question: {message}"""
    else:
        # Lean general prompt. Capped length to control output tokens.
        prompt = f"""You are a friendly representative for DocuRoute AI, which sells
industrial food-processing machinery. Reply in 1-2 short sentences. If the user
seems interested in buying, warmly invite them to ask about a specific machine.

Message: {message}"""

    response = llm.invoke(prompt)
    return {"final_answer": response.content}

# ---------------------------------------------------------
# EDGES
# ---------------------------------------------------------
def route_to_next(state: AgentState):
    return "retrieve_specs" if state["intent"] == "TECHNICAL" else "general_chat"

# ---------------------------------------------------------
# COMPILE
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

if __name__ == "__main__":
    print("\n=== DOCUROUTE ENGINE ONLINE ===\n")
    for msg in ["Hello there!", "Hi, I'm looking to buy some machines.",
                "What is the voltage of the Industrial Steam Cooker?"]:
        print(f"USER: {msg}")
        result = app.invoke({"user_message": msg})
        print(f"OUTPUT: {result['final_answer']}\n{'-'*50}")