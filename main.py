import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Importing the compiled LangGraph engine under the correct enterprise namespace
from agent import app as docuroute_agent  

# 1. Enterprise Observability: Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("DocuRouteGateway")

# Initialize FastAPI Microservice
app = FastAPI(title="DocuRoute AI API Gateway (CFTech Modernization)", version="1.1.0")

# 2. Hardened Perimeter (CORS): Passes B2B procurement audits while allowing local dev
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://docuroute-ai.vercel.app", # <-- The exact URL from your screenshot
    os.getenv("FRONTEND_PRODUCTION_URL", "https://cftech.in")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS, 
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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
    """Decoy endpoint to keep Render awake without triggering expensive LLM compute."""
    return {"status": "DocuRoute AI gateway is active, isolated, and non-blocking."}

# Primary AI Routing Endpoint with Apex Redundancy & Async Non-Blocking Execution
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        logger.info(f"Incoming payload received. Length: {len(request.message)} chars")
        
        # 3. The Asphyxiation Patch: Using await and .ainvoke() to keep the ASGI event loop open
        result = await docuroute_agent.ainvoke({"user_message": request.message})
        
        # Extract the final state variables
        final_answer = result.get("final_answer", "Error generating technical response.")
        detected_intent = result.get("intent", "UNKNOWN")
        
        logger.info(f"Execution resolved successfully. Routed Intent: {detected_intent}")
        return ChatResponse(response=final_answer, intent=detected_intent)
        
    except Exception as e:
        # The Apex Standard: Catch at the edge, capture full stack trace in Render logs, never drop the client.
        logger.error(f"CRITICAL: DocuGraph execution failed. Error: {str(e)}", exc_info=True)
        
        # Return a graceful, structured B2B degradation matching the Pydantic schema perfectly
        return ChatResponse(
            response="Our technical specification retrieval engine is currently experiencing upstream network latency. Please try again in 60 seconds.",
            intent="ERROR_FALLBACK"
        )