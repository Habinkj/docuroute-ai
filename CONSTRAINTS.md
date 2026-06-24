# Current Operational Constraints & Bottlenecks

## 1. The "Router Tax"
*   **The Bottleneck:** Technical queries currently require two sequential LLM calls: one for intent classification (~60 tokens) and one for final RAG generation (~2500 tokens). This adds ~0.5s latency to technical responses.
*   **The Constraint:** Any architectural suggestions must NOT increase this router tax. Latency optimization is paramount.

## 2. Strict Hallucination Guardrails
*   **The Bottleneck:** Industrial clients cannot afford hallucinated specs (e.g., incorrect hydraulic fluid viscosities). 
*   **The Constraint:** The RAG pipeline must remain completely sandboxed. If the exact answer is not in the top-k ChromaDB chunks, the system must definitively state: "I must escalate to the engineering team." No synthetic generation allowed.

## 3. API Gateway Load
*   **The Bottleneck:** Render free-tier spin-down. 
*   **The Constraint:** The `/health` endpoint is currently used as a keep-alive. Future scaling must account for cold-start mitigation without burning compute.