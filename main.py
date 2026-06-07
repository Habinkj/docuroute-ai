from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import app as langgraph_app  # This imports the compiled brain from agent.py

app = FastAPI()

# 1. The Vercel Gatekeeper (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. The Data Structure
class ChatRequest(BaseModel):
    message: str

# 3. The LangGraph Endpoint
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    print(f"Incoming message from frontend: {request.message}")
    
    try:
        # Feed the user's message into the LangGraph state machine
        result = langgraph_app.invoke({"user_message": request.message})
        
        # Extract the final answer from the state dictionary
        bot_reply = result.get("final_answer", "Error: No answer generated.")
        
        # THE FIX: Aligning the JSON keys with the Next.js Armor Plate
        return {
            "role": "assistant",
            "content": bot_reply
        }
        
    except Exception as e:
        print(f"LangGraph execution failed: {e}")
        # THE FIX: The fallback error must also bypass the Armor Plate
        return {
            "role": "assistant",
            "content": "I am currently undergoing maintenance. Please contact the DocuRoute AI sales team directly."
        }