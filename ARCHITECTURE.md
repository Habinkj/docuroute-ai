# DocuRoute AI: System Architecture Map

## 1. System Overview
DocuRoute AI is a decoupled, white-label B2B copilot designed for the heavy industrial sector. It uses an autonomous LangGraph state machine to route queries, bypassing expensive RAG pipelines for general chatter and enforcing strict semantic retrieval for technical specifications.

## 2. Tech Stack
*   **Frontend:** Next.js (React) hosted on Vercel.
*   **API Gateway:** Python FastAPI hosted on Render.
*   **AI Orchestration:** LangGraph & LangChain.
*   **LLM:** Gemini 2.5 Flash.
*   **Vector Database:** Local ChromaDB (Semantic Chunking).

## 3. Data Flow & Routing Logic
1.  **Client Request:** Next.js sends JSON payload to FastAPI `/api/chat`.
2.  **Validation:** FastAPI enforces `ChatRequest` Pydantic schema.
3.  **State Machine Entry:** Payload enters LangGraph `route_intent` node.
4.  **Intent Classification (The Fork):**
    *   *Path A (GENERAL):* Bypasses DB. Routes to lightweight LLM prompt. Cost: ~100 tokens. Latency: < 1s.
    *   *Path B (TECHNICAL):* Triggers ChromaDB `retrieve_specs` node. Executes semantic similarity search (k=3) against the Caterpillar Fluid Specs catalog.
5.  **State Convergence:** Both paths resolve at `generate_answer` node.
6.  **Response:** Payload streams back through FastAPI to the client.