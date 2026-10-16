import httpx
import asyncio

BASE_URL = "http://127.0.0.1:8000"

async def simulate_legitimate_user():
    print("\n--- SIMULATING LEGITIMATE USER ---")
    async with httpx.AsyncClient() as client:
        # Standard browser User-Agent
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                   "Authorization": "Bearer valid_token_123"}
        response = await client.get(f"{BASE_URL}/api/products", headers=headers)
        
        print(f"GET /api/products -> HTTP {response.status_code}")
        print(f"Headers Received: Score={response.headers.get('X-SHIELD-Score')}, Latency={response.headers.get('X-SHIELD-Latency')}")
        print(f"Body: {response.json()}")

async def simulate_web_scraper():
    print("\n--- SIMULATING WEB SCRAPER (Layer 5 Block) ---")
    async with httpx.AsyncClient() as client:
        # Using a known bad User-Agent that we hashed in app.py
        headers = {"User-Agent": "Scrapy/2.11.0"}
        response = await client.get(f"{BASE_URL}/api/products", headers=headers)
        
        print(f"GET /api/products -> HTTP {response.status_code}")
        print(f"Reason: {response.json().get('error')}")

async def simulate_graphql_attack():
    print("\n--- SIMULATING GRAPHQL DEEP QUERY ATTACK (Layer 4 Block) ---")
    async with httpx.AsyncClient() as client:
        headers = {"User-Agent": "Mozilla/5.0",
                   "Authorization": "Bearer valid_token_123"}
        # A query with a nesting depth of 7. Our limit in app.py is 5.
        deep_query = "{ user { orders { products { reviews { author { profile { settings } } } } } } }"
        
        response = await client.post(
            f"{BASE_URL}/graphql", 
            json={"query": deep_query},
            headers=headers
        )
        print(f"POST /graphql -> HTTP {response.status_code}")
        print(f"Reason: {response.json().get('error')}")

async def simulate_credential_stuffing():
    print("\n--- SIMULATING CREDENTIAL STUFFING (Layer 3 Block) ---")
    async with httpx.AsyncClient() as client:
        # We use a suspicious scripting User-Agent
        headers = {"User-Agent": "python-requests/2.31.0"}
        
        # Fire a rapid burst of 25 requests to trigger the ML rate anomaly
        for i in range(25):
            response = await client.post(
                f"{BASE_URL}/api/login", 
                json={"username": f"stolen_user_{i}", "password": "password123"},
                headers=headers
            )
            
            # Print the exact moment the ML model drops the hammer
            if response.status_code == 403:
                print(f"Attempt {i+1}: POST /api/login -> HTTP 403")
                print(f"Blocked at: Layer 3 (ML Anomaly Detector)")
                print(f"Reason: {response.json().get('error')}")
                break
            else:
                print(f"Attempt {i+1}: HTTP {response.status_code} (Gathering anomaly score...)")

async def main():
    print("Starting Attack Simulations against SHIELD-API...\n")
    await simulate_legitimate_user()
    await asyncio.sleep(1)
    await simulate_web_scraper()
    await asyncio.sleep(1)
    await simulate_graphql_attack()
    await asyncio.sleep(1)
    await simulate_credential_stuffing()
    
if __name__ == "__main__":
    asyncio.run(main())

