import requests
import time

# Ensure your FastAPI server is running locally on port 8000
API_URL = "http://localhost:8000/api/chat"

# The 20 Realistic Test Queries
queries = [
    # 10 Technical (Should hit Vector DB)
    "What is the operating voltage of the hydraulic press?",
    "Show me the viscosity requirements for the compressor.",
    "What is the maximum torque capacity?",
    "Explain the safety manual procedures for the boiler.",
    "What is the pressure limit on the primary valve?",
    "Give me the machine specifications for model X-200.",
    "How does the cooling system work?",
    "What are the maintenance intervals for the motor?",
    "List the physical dimensions of the industrial cooker.",
    "What is the power consumption in kilowatts?",
    
    # 10 General (Should hit the Zero-Cost Cascade)
    "Hello there!",
    "I am looking to buy some equipment for my factory.",
    "Who am I talking to?",
    "Can I get a quote for a bulk order?",
    "Thanks for the help earlier.",
    "Are you a human or a bot?",
    "I need to speak to a sales representative.",
    "Good morning.",
    "Do you ship internationally?",
    "What is your company's return policy?"
]

print("Starting telemetry load test...\n")

for i, query in enumerate(queries):
    start_time = time.time()
    try:
        response = requests.post(API_URL, json={"message": query})
        status = response.json().get("intent", "FAILED")
    except Exception as e:
        status = "CRITICAL FAILURE"
        
    latency = round(time.time() - start_time, 2)
    print(f"[{i+1}/20] {status} | {latency}s | {query}")

print("\nTest complete. Open LangSmith to calculate token drops.")