from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from agent import app as kiliyara_agent  # Importing the compiled LangGraph engine

# Initialize FastAPI Microservice
app = FastAPI(title="Kiliyara AI API Gateway", version="1.0.0")

# Configure CORS for decoupled frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this to your Vercel domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schema Validation
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    intent: str

# Health Check Endpoint (Keep-Alive for Render Free Tier)
@app.get("/health")
async def health_check():
    """Decoy endpoint to keep Render awake without triggering Gemini."""
    return {"status": "Kiliyara AI backend is active and operational."}

# Primary AI Routing Endpoint with Apex Fault Tolerance
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Trigger the LangGraph state machine
        result = kiliyara_agent.invoke({"user_message": request.message})
        
        # Extract the final state variables
        final_answer = result.get("final_answer", "Error generating response.")
        detected_intent = result.get("intent", "UNKNOWN")
        
        return ChatResponse(response=final_answer, intent=detected_intent)
        
    except Exception as e:
        # The Apex Standard: Never fail silently, never crash the ASGI worker.
        logging.error(f"CRITICAL: Engine invocation failed. Error: {str(e)}")
        
        # Return a graceful, structured degradation to the frontend matching the Pydantic schema
        return ChatResponse(
            response="Our technical retrieval engine is currently experiencing high latency. Please try again in 60 seconds.",
            intent="ERROR_FALLBACK"
        )