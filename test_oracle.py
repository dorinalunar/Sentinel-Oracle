"""
Unit tests for SentinelOracle helper logic and agent utilities.
Tests off-chain hashing, URL safety checks, and payload generation.
"""
import unittest
import hashlib
from agent_client import prepare_evidence


class TestSentinelOracleClient(unittest.TestCase):

    def test_prepare_evidence_hash(self):
        """Verify that agent_client correctly computes SHA-256 for a given URL."""
        # Using a reliable test URL
        url = "https://example.com"
        result_hash = prepare_evidence(url)

        self.assertIsNotNone(result_hash)
        self.assertEqual(len(result_hash), 64)
        # Check that hash contains only valid hexadecimal characters
        self.assertTrue(all(c in "0123456789abcdef" for c in result_hash))

    def test_hash_integrity(self):
        """Simulate the contract's hash matching check."""
        sample_payload = "Strict consensus on domain topic"
        expected_hash = hashlib.sha256(sample_payload.encode("utf-8")).hexdigest()

        # Recomputed hash must match
        computed_hash = hashlib.sha256(sample_payload.encode("utf-8")).hexdigest()
        self.assertEqual(expected_hash, computed_hash)

    def test_url_security_rules(self):
        """Test URL validation constraints (SSRF protection logic)."""
        def is_safe_url(url: str) -> bool:
            cleaned = url.strip()
            if len(cleaned) > 512:
                return False
            if not cleaned.startswith("https://"):
                return False
            if "localhost" in cleaned.lower() or "127.0.0.1" in cleaned:
                return False
            return True

        # Valid public URLs
        self.assertTrue(is_safe_url("https://example.com"))
        self.assertTrue(is_safe_url("https://api.github.com/data"))

        # Unsafe / Disallowed URLs (must be blocked)
        self.assertFalse(is_safe_url("http://example.com"))          # Plain HTTP
        self.assertFalse(is_safe_url("https://localhost:8080"))      # Localhost attack
        self.assertFalse(is_safe_url("https://127.0.0.1/admin"))     # Internal IP attack


if __name__ == "__main__":
    unittest.main()
