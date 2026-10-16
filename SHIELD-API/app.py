from os import fsync

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import time 
import hashlib
import json

#Initialize the live web server
app = FastAPI(
    title = "SHIELD-API",
    description = "Scalable Hybrid Intelligent Engine for Layered Defence of APIs"
)

# Simulate Infrastructure

# 1. Simulate Redis (Layer 2 - Adaptive Rate Limiting)
# In production, this would be a real Redis cluster. Here, it is a dictionary in memory
rate_limit_store = {}

# 2. Known Bad Fingerprints (Layer 5 - Bot Fingerprinting)
# Simulating the JA3 database. We hash common bot User-Agents for the prototype
# Removed python-requests from Layer 5 so Layer 3's ML can catch it instead
KNOWN_BAD_HASHES = {
    hashlib.md5(b"Scrapy/2.11.0").hexdigest()
}

# 3. Simplified ML Scoring Engine (Layer 3 - Anomaly Detector)
def calculate_anomaly_score(request_data: dict) -> float:
    """A simplified heuristic scoring engine mimicking our Isolation Forest for the live demo."""
    score = 0.1 # Base score for normal traffic

    #Heuristics that the ML model learned in simulate.py
    if request_data.get("rate", 0) > 15:
        score += 0.5 # High speed = suspicious
    if request_data.get("is_graphql", False) and request_data.get("depth", 0) > 5:
        score += 0.7 # Deep GraphQL query = highly anomalous
    if request_data.get("user_agent", "") == "python-requests/2.31.0":
        score += 0.6 # Default script tool = suspicious

    return min(score, 1.0) # Cap teh score at 1.0

@app.middleware("http")
async def shield_api_middleware(request: Request, call_next):
    """The core security gate. Every request passes through here before hitting the endpoint."""
    start_time = time.time()
    client_ip = request.client.host
    path = request.url.path

    # Track which layers the request successfully passes
    layers_passed = []

    # Layer 0 & 5: Edge Filter & Bot Fingerprinter (Passive)
    # We simulate checking the TLS/JA3 hash by hashing the User-Agent
    user_agent = request.headers.get("user-agent","")
    ua_hash = hashlib.md5(user_agent.encode()).hexdigest()

    if ua_hash in KNOWN_BAD_HASHES:
        return JSONResponse(status_code=403, content={"error": "Blocked at Layer 5: Known malicious bot fingerprint"})
    layers_passed.append("L0_Edge")
    layers_passed.append("L5_Bot")

    # Layer 1: Authentication Gate
    # Some pages (like login and docs) must be public. Everything else requires a token.
    public_endpoints = ["/api/login", "/health", "/docs", "/openapi.json"]
    if path not in public_endpoints:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(status_code=401, content={"error": "Blocked at Layer 1: Missing Authentication (Unauthorized)."})
    layers_passed.append("L1_Auth")

    # Layer 3: ML Anomaly Detector
    # We calculate the ML score BEFORE rate limiting so the rate limiter can adapt
    request_data = {
        "rate": rate_limit_store.get(client_ip, 0),
        "user_agent": user_agent,
        "is_graphql": path == "/graphql"
    }
    anomaly_score = calculate_anomaly_score(request_data)

    # The absolute block threshold 
    if anomaly_score > 0.75:
        return JSONResponse(status_code=403, content={"error": f"Blocked at Layer 3: Anomaly score {anomaly_score} exceeds 0.75 threshold."})
    layers_passed.append("L3_ML")

    # Layer 2: Adaptive Rate Limiter
    # Adaptive Logic: If the ML model is suspicious (>0.5), shrink the bucket to 20
    current_limit = 20 if anomaly_score > 0.50 else 100
    
    current_requests = rate_limit_store.get(client_ip, 0)
    if current_requests >= current_limit:
        return JSONResponse(status_code=429, content={"error": f"Blocked at Layer 2: Rate limit of {current_limit} exceeded."})
    
    # Add token to bucket
    rate_limit_store[client_ip] = current_requests + 1
    layers_passed.append("L2_RateLimiter")

    # Passed. Send request to the actual application endpoint
    response = await call_next(request)

    # Add Custom Security Headers to the final response
    process_time_ms =  (time.time() - start_time) * 1000
    response.headers["X-SHIELD-Score"] = str(round(anomaly_score, 2))
    response.headers["X-SHIELD-Layers"] = ", ".join(layers_passed)
    response.headers["X-SHIELD-Latency"] = f"{process_time_ms:.2f}ms"

    return response


from pydantic import BaseModel

# Data Models
class LoginRequest(BaseModel):
    username: str
    password: str

class GraphQLRequest(BaseModel):
    query: str

# API ENDPOINTS
@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return{"status": "healthy", "version": "1.0.0"}

@app.get("/api/products")
async def get_products():
    """Returns a list of products"""
    return {"data": [{"id": 1, "name": "Secure API Gateway"}, {"id": 2, "name": "ML Defense Shield"}]}

@app.get("/api/user/{user_id}")
async def get_user(user_id: int):
    """Returns data for a specific user"""
    return {"data": {"id":user_id, "name":f"User_{user_id}", "role":"admin"}}

@app.post("/api/login")
async def login(credentials: LoginRequest):
    """Simulates a login endpoint"""
    # In a real app, we verify passwords against a database here.
    if credentials.username == "admin" and credentials.password == "password":
        return {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake_token_data"}
    return JSONResponse(status_code=401, content={"error": "Invalid credentials"})

# LAYER 4 & GRAPHQL ENDPOINT

@app.post("/graphql")
async def graphql_endpoint(request: GraphQLRequest):
    """The GraphQL endpoint, featuring Layer 4 Defences."""
    query = request.query
    
    # 1. Introspection Blocking (Production Mode)
    if "__schema" in query or "__type" in query:
        return JSONResponse(status_code=403, content={"error": "Blocked at Layer 4: GraphQL Introspection is disabled in production."})
    
    # 2. Query Depth Calculation (Manual Parsing Prototype)
    # We calculate the depth by tracking the maximum nesting of '{' brackets.
    current_depth = 0
    max_depth = 0
    for char in query:
        if char == '{':
            current_depth += 1
            if current_depth > max_depth:
                max_depth = current_depth
        elif char == '}':
            current_depth -= 1
            
    # The absolute limit from the report is 5.
    if max_depth > 5:
        return JSONResponse(
            status_code=400, 
            content={"error": f"Blocked at Layer 4: Query depth {max_depth} exceeds maximum limit of 5."}
        )
        
    # If it passes Layer 4, return the fake GraphQL data
    return {"data": {"message": "GraphQL query executed successfully!", "depth_processed": max_depth}}