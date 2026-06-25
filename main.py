import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import app as docuroute_agent

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("DocuRouteGateway")

app = FastAPI(title="DocuRoute AI API Gateway", version="1.1.0")

# CORS: every origin the frontend is served from.
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://docuroute-ai.vercel.app",   # live frontend
    os.getenv("FRONTEND_PRODUCTION_URL", ""),
]
# Drop empty entries so an unset env var doesn't add a blank origin.
ALLOWED_ORIGINS = [o for o in ALLOWED_ORIGINS if o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    intent: str


@app.get("/health")
async def health_check():
    """Keep-alive for Render free tier - no LLM compute."""
    return {"status": "active"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        logger.info(f"Incoming payload. Length: {len(request.message)} chars")

        # Async ainvoke keeps the ASGI event loop unblocked under concurrency.
        result = await docuroute_agent.ainvoke({"user_message": request.message})

        final_answer = result.get("final_answer", "Error generating response.")
        detected_intent = result.get("intent", "UNKNOWN")

        logger.info(f"Resolved. Intent: {detected_intent}")
        return ChatResponse(response=final_answer, intent=detected_intent)

    except Exception as e:
        logger.error(f"Execution failed: {str(e)}", exc_info=True)
        return ChatResponse(
            response="The retrieval engine is experiencing upstream latency. Please try again shortly.",
            intent="ERROR_FALLBACK",
        )