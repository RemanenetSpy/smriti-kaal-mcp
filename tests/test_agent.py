"""Quick test: ingest events then verify agent can recall them."""
import httpx

API = "http://localhost:8000"

# Step 1: Generate key
key_resp = httpx.post(f"{API}/billing/keys?tier=explorer")
key_data = key_resp.json()
KEY = key_data["api_key"]
SRC = key_data["source_id"]
H = {"X-API-Key": KEY}
print(f"=== KEY: {KEY[:20]}... SOURCE: {SRC} ===")

# Step 2: Ingest with a DIFFERENT source_id (simulates dashboard)
ingest = httpx.post(f"{API}/ingest", headers=H, json={
    "source_id": "my-crm",
    "events": [
        {"text": "Tesla signed a 2 million dollar partnership with SpaceX on April 10"},
        {"text": "Our team completed the website redesign for Nike last week"},
    ]
})
data = ingest.json()
print(f"Ingested: {data['ingested_count']} events")
for svo in data.get("svo_tuples", []):
    print(f"  SVO: {svo['subject']} | {svo['verb']} | {svo['object']}")

# Step 3: Agent chat - can it find them?
print("\n=== AGENT CHAT ===")
chat = httpx.post(f"{API}/agent/run", headers=H, json={
    "prompt": "What do you know about Tesla or Nike?",
}, timeout=30)
resp = chat.json()
print(f"Events retrieved: {resp['events_retrieved']}")
print(f"Agent says:\n{resp['response'][:500]}")
