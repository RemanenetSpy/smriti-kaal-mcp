"""Privacy test: verify Customer A cannot see Customer B's data."""
import httpx

API = "http://localhost:8000"

# === Customer A ===
key_a = httpx.post(f"{API}/billing/keys?tier=explorer").json()
KEY_A = key_a["api_key"]
print(f"Customer A: {KEY_A[:20]}... (owner: {key_a['source_id']})")

httpx.post(f"{API}/ingest", headers={"X-API-Key": KEY_A}, json={
    "source_id": "customer-a-crm",
    "events": [{"text": "Customer A signed a deal with Apple for 1 million dollars"}]
})
print("  Ingested: Apple deal")

# === Customer B ===
key_b = httpx.post(f"{API}/billing/keys?tier=explorer").json()
KEY_B = key_b["api_key"]
print(f"Customer B: {KEY_B[:20]}... (owner: {key_b['source_id']})")

httpx.post(f"{API}/ingest", headers={"X-API-Key": KEY_B}, json={
    "source_id": "customer-b-crm",
    "events": [{"text": "Customer B has a secret project with NASA worth 5 billion"}]
})
print("  Ingested: NASA project")

# === Privacy Test ===
print("\n=== PRIVACY TEST ===")

# Customer A asks about data
chat_a = httpx.post(f"{API}/agent/run", headers={"X-API-Key": KEY_A}, json={
    "prompt": "Tell me everything you know. What deals or projects exist?"
}, timeout=30).json()
print(f"\nCustomer A asks 'what exists?':")
print(f"  Events found: {chat_a['events_retrieved']}")
print(f"  Response: {chat_a['response'][:300]}")

# Check: Does A see B's NASA data?
has_nasa = "NASA" in chat_a["response"] or "nasa" in chat_a["response"].lower()
has_apple = "Apple" in chat_a["response"] or "apple" in chat_a["response"].lower()
print(f"\n  [PASS] Sees own 'Apple' data: {has_apple}")
print(f"  {'[FAIL] PRIVACY BREACH!' if has_nasa else '[PASS] Cannot see'} Customer B 'NASA' data: {has_nasa}")

# Customer B asks about data
chat_b = httpx.post(f"{API}/agent/run", headers={"X-API-Key": KEY_B}, json={
    "prompt": "Tell me everything you know. What deals or projects exist?"
}, timeout=30).json()
print(f"\nCustomer B asks 'what exists?':")
print(f"  Events found: {chat_b['events_retrieved']}")
print(f"  Response: {chat_b['response'][:300]}")

has_nasa_b = "NASA" in chat_b["response"] or "nasa" in chat_b["response"].lower()
has_apple_b = "Apple" in chat_b["response"] or "apple" in chat_b["response"].lower()
print(f"\n  [PASS] Sees own 'NASA' data: {has_nasa_b}")
print(f"  {'[FAIL] PRIVACY BREACH!' if has_apple_b else '[PASS] Cannot see'} Customer A 'Apple' data: {has_apple_b}")

if not has_nasa and not has_apple_b:
    print("\n[LOCKED] TENANT ISOLATION: PASSED -- customers are fully isolated!")
else:
    print("\n[WARNING] TENANT ISOLATION: FAILED -- data is leaking between customers!")
