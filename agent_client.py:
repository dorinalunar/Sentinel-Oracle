"""
Helper utility for SentinelOracle agents.
Fetches web content, calculates the deterministic SHA-256 fingerprint,
and outputs the parameters required for on-chain evidence submission.
"""
import hashlib
import requests

def prepare_evidence(url: str, max_payload: int = 20000) -> str | None:
    try:
        response = requests.get(url, timeout=10)
        body = response.text[:max_payload]
        content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

        print(f"--- Evidence Prepared for: {url} ---")
        print(f"HTTP Status  : {response.status_code}")
        print(f"Content Hash : {content_hash}")
        print("\nUse this content_hash when calling 'provide_evidence' on-chain.")
        return content_hash
    except Exception as error:
        print(f"Failed to fetch content: {error}")
        return None

if __name__ == "__main__":
    test_target = "https://example.com"
    prepare_evidence(test_target)
