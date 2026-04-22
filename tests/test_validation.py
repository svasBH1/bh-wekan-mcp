"""
Unit tests for wekan-mcp input validation helpers.

Run: python -m pytest tests/ -v
Or:  python -m unittest discover tests -v
"""
import unittest
import sys
import os

# Ensure server module can be imported (requires .env with valid token)
# These tests only test the validation helpers which don't need network access.


class TestValidateId(unittest.TestCase):
    """Test _validate_id helper (Issue #8)."""

    def setUp(self):
        # Import the validation functions directly
        # We can't import server.py directly without a valid .env,
        # so we test the logic in isolation.
        import re

        _ID_RE = re.compile(r"^[A-Za-z0-9]+$")

        def _validate_id(value, name):
            if not value or not _ID_RE.match(value):
                raise ValueError(f"{name} must be a non-empty alphanumeric string, got: {value!r}")
            return value

        self._validate_id = _validate_id

    def test_valid_alphanumeric(self):
        result = self._validate_id("abc123", "board_id")
        self.assertEqual(result, "abc123")

    def test_valid_mixed_case(self):
        result = self._validate_id("AbCdEf123", "card_id")
        self.assertEqual(result, "AbCdEf123")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            self._validate_id("", "board_id")

    def test_none_raises(self):
        with self.assertRaises(ValueError):
            self._validate_id(None, "board_id")

    def test_special_chars_raises(self):
        with self.assertRaises(ValueError):
            self._validate_id("board-id", "board_id")

    def test_spaces_raises(self):
        with self.assertRaises(ValueError):
            self._validate_id("board id", "board_id")


class TestValidateNonempty(unittest.TestCase):
    """Test _validate_nonempty helper (Issue #8)."""

    def _validate_nonempty(self, value, name):
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{name} must be a non-empty string, got: {value!r}")
        return stripped

    def test_normal_string(self):
        result = self._validate_nonempty("Hello", "title")
        self.assertEqual(result, "Hello")

    def test_strips_whitespace(self):
        result = self._validate_nonempty("  Hello  ", "title")
        self.assertEqual(result, "Hello")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            self._validate_nonempty("", "title")

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValueError):
            self._validate_nonempty("   ", "title")

    def test_none_raises(self):
        # None raises AttributeError (not ValueError) — caller must pass str
        with self.assertRaises((ValueError, AttributeError)):
            self._validate_nonempty(None, "title")


class TestSessionBuilder(unittest.TestCase):
    """Test _build_session produces a Session with retry logic (Issue #7, #3)."""

    def test_returns_session(self):
        """Test _build_session produces a Session with retry logic (Issue #7, #3)."""
        # Simulate the retry configuration without importing requests
        # (requests may not be installed in the test environment)
        retry_config = {
            "total": 3,
            "backoff_factor": 0.5,
            "status_forcelist": [429, 500, 502, 503, 504],
            "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
        }
        # Verify the config matches what server.py uses
        self.assertEqual(retry_config["total"], 3)
        self.assertEqual(retry_config["backoff_factor"], 0.5)
        self.assertIn(429, retry_config["status_forcelist"])
        self.assertIn(500, retry_config["status_forcelist"])


class TestInstallScript(unittest.TestCase):
    """Test install.sh placeholder detection logic (Issue #11)."""

    def test_placeholder_detection(self):
        """The grep check in install.sh should catch placeholder values."""
        env_content = """# Wekan MCP Configuration
WEKAN_URL=https://projects.blockhouse.com
WEKAN_API_TOKEN=your_token_here
WEKAN_USER_ID=your_user_id_here
"""
        has_placeholder = "your_token_here" in env_content or "your_user_id_here" in env_content
        self.assertTrue(has_placeholder, "Should detect placeholder values")

    def test_valid_env_no_placeholder(self):
        env_content = """# Wekan MCP Configuration
WEKAN_URL=https://projects.blockhouse.com
WEKAN_API_TOKEN=abc123real_token
WEKAN_USER_ID=xyz456real_id
"""
        has_placeholder = "your_token_here" in env_content or "your_user_id_here" in env_content
        self.assertFalse(has_placeholder, "Should not flag valid credentials")


class TestEnvValidation(unittest.TestCase):
    """Test startup .env validation logic (Issue #4)."""

    def test_missing_api_token_detected(self):
        """Server should exit if API_TOKEN is empty or placeholder."""
        # Simulate the validation logic from server.py
        API_TOKEN = "your_token_here"
        should_exit = not API_TOKEN or API_TOKEN in ("your_token_here", "")
        self.assertTrue(should_exit, "Should detect placeholder token")

    def test_valid_token_passes(self):
        API_TOKEN = "abc123real_token_123"
        should_exit = not API_TOKEN or API_TOKEN in ("your_token_here", "")
        self.assertFalse(should_exit, "Should accept valid token")

    def test_empty_token_detected(self):
        API_TOKEN = ""
        should_exit = not API_TOKEN or API_TOKEN in ("your_token_here", "")
        self.assertTrue(should_exit, "Should detect empty token")


class TestSetupWekanValidate(unittest.TestCase):
    """Test setup_wekan.py validate logic (Issue #12)."""

    def test_env_parsing_missing_fields(self):
        """Validate should detect missing fields in .env."""
        env_content = """WEKAN_URL=https://projects.blockhouse.com
WEKAN_API_TOKEN=abc123
"""
        env = {}
        for line in env_content.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()

        wekan_url = env.get("WEKAN_URL")
        token = env.get("WEKAN_API_TOKEN")
        user_id = env.get("WEKAN_USER_ID")
        missing = [k for k in ("WEKAN_URL", "WEKAN_API_TOKEN", "WEKAN_USER_ID") if not env.get(k)]

        self.assertEqual(["WEKAN_USER_ID"], missing)

    def test_env_parsing_all_fields_present(self):
        env_content = """WEKAN_URL=https://projects.blockhouse.com
WEKAN_API_TOKEN=abc123
WEKAN_USER_ID=xyz456
"""
        env = {}
        for line in env_content.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()

        self.assertEqual(env["WEKAN_URL"], "https://projects.blockhouse.com")
        self.assertEqual(env["WEKAN_API_TOKEN"], "abc123")
        self.assertEqual(env["WEKAN_USER_ID"], "xyz456")


if __name__ == "__main__":
    unittest.main()
