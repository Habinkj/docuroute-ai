import os
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langgraph.graph import StateGraph, END

# 1. Unlock the Vault
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("CRITICAL: GEMINI_API_KEY not found.")

# 2. Connect to the Chroma Brain (The folder you just built)
print("Connecting to Vector Database...")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
vector_db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
retriever = vector_db.as_retriever(search_kwargs={"k": 3}) # Fetches top 3 chunks

# 3. Initialize the Core LLM (The Thinker)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# ---------------------------------------------------------
# LANGGRAPH ARCHITECTURE
# ---------------------------------------------------------

# 4. Define the State (The Briefcase)
# This dictionary gets passed between every single node in the circuit.
class AgentState(TypedDict):
    user_message: str
    intent: str
    technical_context: str
    final_answer: str

# 5. Node A: The Router (The Manager)
def route_intent(state: AgentState):
    print("--- NODE: ROUTER ---")
    message = state["user_message"]
    
    # We ask the LLM to classify the user's message
    prompt = f"""You are an intelligent router for DocuRoute AI, a manufacturing company. 
    Analyze the user's message and output exactly one word: 'TECHNICAL' if they are asking about machine specifications, features, or how things work. Output 'GENERAL' if they are just saying hello or asking non-machine questions.
    User Message: {message}"""
    
    response = llm.invoke(prompt)
    intent = response.content.strip().upper()
    
    print(f"Detected Intent: {intent}")
    return {"intent": intent}

# ---------------------------------------------------------
# THE WORKERS (NODES)
# ---------------------------------------------------------

# Node B: The RAG Engineer
def retrieve_specs(state: AgentState):
    print("--- NODE: RAG ENGINEER ---")
    message = state["user_message"]
    
    # Query the Chroma database for the most relevant PDF chunks
    docs = retriever.invoke(message)
    context = "\n\n".join([doc.page_content for doc in docs])
    
    print(f"Retrieved {len(docs)} chunks of technical data.")
    return {"technical_context": context}

# Node C: The General Receptionist
def general_chat(state: AgentState):
    print("--- NODE: GENERAL RECEPTIONIST ---")
    # No database query needed for general chatter
    return {"technical_context": "No technical context needed. Be polite and professional."}

# Node D: The Formatter (The Speaker)
def generate_answer(state: AgentState):
    print("--- NODE: FORMATTER ---")
    intent = state["intent"]
    context = state.get("technical_context", "")
    message = state["user_message"]
    
    # The AI changes its personality based on the route
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

# This is the brain of the routing logic.
def route_to_next(state: AgentState):
    if state["intent"] == "TECHNICAL":
        print("TRAFFIC CONTROL: Routing to Vector Database...")
        return "retrieve_specs"
    else:
        print("TRAFFIC CONTROL: Routing to General Chat...")
        return "general_chat"


# ---------------------------------------------------------
# COMPILE THE SYSTEM
# ---------------------------------------------------------

print("Compiling LangGraph Engine...")
workflow = StateGraph(AgentState)

# 1. Register all the nodes
workflow.add_node("route_intent", route_intent)
workflow.add_node("retrieve_specs", retrieve_specs)
workflow.add_node("general_chat", general_chat)
workflow.add_node("generate_answer", generate_answer)

# 2. Define the flow
workflow.set_entry_point("route_intent")

# The conditional edge points to our traffic controller function
workflow.add_conditional_edges("route_intent", route_to_next)

# Both pathways eventually lead to the formatter, which ends the circuit
workflow.add_edge("retrieve_specs", "generate_answer")
workflow.add_edge("general_chat", "generate_answer")
workflow.add_edge("generate_answer", END)

# 3. Lock it in
app = workflow.compile()


# ---------------------------------------------------------
# LOCAL TESTING TERMINAL
# ---------------------------------------------------------
if __name__ == "__main__":
    print("\n=== DocuRoute AI ENTERPRISE AI ONLINE ===\n")
    
    # Test 1: Technical Query
    test_message_1 = "What is the voltage of the Industrial Steam Cooker?"
    print(f"USER: {test_message_1}")
    result_1 = app.invoke({"user_message": test_message_1})
    print(f"\nFINAL OUTPUT:\n{result_1['final_answer']}\n")
    print("-" * 50)
    
    # Test 2: General Query
    test_message_2 = "Hi, I am looking to buy some machines."
    print(f"USER: {test_message_2}")
    result_2 = app.invoke({"user_message": test_message_2})
    print(f"\nFINAL OUTPUT:\n{result_2['final_answer']}\n")