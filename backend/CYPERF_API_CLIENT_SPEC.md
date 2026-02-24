# Cyperf API Wrapper Specification

This document defines the exact interface required for the `cyperf-api-wrapper` package that the sync service depends on.

---

## Overview

The `cyperf-api-wrapper` is a Python package that provides a client library for interacting with Keysight Cyperf Controller's REST API. The sync service uses this wrapper to fetch attack profiles and extract CVE associations.

---

## Package Requirements

### Installation

```bash
pip install cyperf-api-wrapper
```

### Version Compatibility

- **Python:** 3.10+
- **FastAPI:** 0.100+
- **SQLAlchemy:** 2.0+
- **Requests:** 2.28+ (for underlying HTTP)

---

## Interface Specification

### CyperfApiClient Class

```python
from cyperf_api_wrapper import CyperfApiClient

class CyperfApiClient:
    """REST client for Keysight Cyperf Controller.

    Handles authentication, connection pooling, and API communication.
    """

    def __init__(
        self,
        controller_address: str,
        username: str,
        password: str,
        verify_ssl: bool = True,
        timeout: int = 30,
    ) -> None:
        """Initialize Cyperf API client.

        Args:
            controller_address: IP address or hostname of Cyperf Controller
                               (e.g., "52.32.20.150")
            username: Username for authentication (e.g., "admin")
            password: Password for authentication (e.g., "CyPerf&Keysight#1")
            verify_ssl: Whether to verify SSL certificates (default: True)
                       Set to False for self-signed certificates in testing
            timeout: Request timeout in seconds (default: 30)

        Raises:
            ConnectionError: If unable to establish connection to controller
            Exception: If any error occurs during initialization.
                      Callers should check if error message contains "401"
                      or "unauthorized" for auth failures.

        Example:
            >>> client = CyperfApiClient(
            ...     controller_address="52.32.20.150",
            ...     username="admin",
            ...     password="CyPerf&Keysight#1"
            ... )
        """
        ...

    def get_all_attack_profiles(self) -> list[dict[str, Any]]:
        """Fetch all attack profiles from Cyperf Controller.

        Returns a list of attack profile objects. Each profile contains
        information about which CVEs it can test.

        Returns:
            List[Dict[str, Any]]: Attack profile objects with this schema:
                {
                    "id": str,           # Unique profile ID (UUID format)
                    "name": str,         # Human-readable profile name
                    "description": str,  # Description of what profile tests
                    "version": str,      # Profile version
                    "enabled": bool,     # Whether profile is active

                    # CVEs this profile can test (choose one format):
                    "cves": [str, ...],  # Direct list of CVE strings

                    # OR
                    "metadata": {
                        "cves": [str, ...],  # CVEs in metadata dict
                        ...  # Other metadata fields
                    },

                    # Optional additional fields
                    "applications": [str, ...],    # Affected applications
                    "attack_technique": str,       # MITRE ATT&CK ID
                    "severity": str,              # Severity level
                    ...
                }

        Raises:
            ConnectionError: If unable to connect to controller
            Exception: If API returns error status. Should include:
                      - "401" or "unauthorized" in message for auth errors
                      - Descriptive message for other errors

        Example:
            >>> profiles = client.get_all_attack_profiles()
            >>> len(profiles)
            247
            >>> profiles[0]["name"]
            'Apache-Log4j-RCE'
            >>> profiles[0]["cves"]
            ['CVE-2021-44228', 'CVE-2021-44229']
        """
        ...

    def close(self) -> None:
        """Close connection to controller and clean up resources.

        Optional method for explicit cleanup. Good practice to call
        in finally block or context manager __exit__.

        Example:
            >>> try:
            ...     client = CyperfApiClient(...)
            ...     profiles = client.get_all_attack_profiles()
            ... finally:
            ...     client.close()
        """
        ...
```

---

## Expected API Responses

### Successful Response: GET /api/v2/attack-profiles

**HTTP Status:** 200 OK

**Response Body:**
```json
{
  "attack_profiles": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Apache-Log4j-RCE",
      "description": "Remote Code Execution via Apache Log4j",
      "version": "2.0",
      "enabled": true,
      "cves": [
        "CVE-2021-44228",
        "CVE-2021-44229",
        "CVE-2021-44230"
      ],
      "metadata": {
        "attack_type": "RCE",
        "severity": "CRITICAL",
        "affected_systems": ["Apache", "Log4j"],
        "attack_technique": "MITRE ATT&CK / T1190",
        "created_date": "2021-12-10",
        "updated_date": "2025-02-20"
      },
      "applications": ["Apache", "Log4j", "Spring", "ActiveMQ"]
    },
    {
      "id": "660f9511-f3ac-52e5-b827-557766551111",
      "name": "Microsoft-Exchange-ProxyLogon",
      "description": "ProxyLogon vulnerabilities in Microsoft Exchange",
      "version": "1.5",
      "enabled": true,
      "cves": [
        "CVE-2021-26855",
        "CVE-2021-26857",
        "CVE-2021-26858",
        "CVE-2021-27065"
      ],
      "metadata": {
        "attack_type": "Remote Code Execution",
        "severity": "CRITICAL"
      },
      "applications": ["Microsoft Exchange Server", "Outlook"]
    }
  ],
  "total_count": 247,
  "page": 1,
  "per_page": 100
}
```

### Error Response: 401 Unauthorized

**HTTP Status:** 401 Unauthorized

**Response Body:**
```json
{
  "error": "Invalid credentials",
  "message": "Authentication failed"
}
```

**Expected Exception:**
```python
raise Exception("401 Unauthorized: Invalid credentials")
# OR
raise ConnectionError("Authentication failed: 401")
```

### Error Response: Network Unreachable

**Expected Exception:**
```python
raise ConnectionError("[Errno 111] Connection refused")
# OR
raise ConnectionError("Unable to connect to 52.32.20.150:443")
```

---

## Implementation Guidelines

### Error Handling

**Do NOT suppress exceptions.** The sync service expects specific exception types:

```python
# Good: Explicit exception types
try:
    response = requests.get(...)
except requests.exceptions.ConnectionError as e:
    raise ConnectionError(f"Failed to connect: {e}") from e

except requests.exceptions.Timeout as e:
    raise ConnectionError(f"Request timeout: {e}") from e

except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        raise Exception(f"401 Unauthorized: {e}") from e
    raise Exception(f"HTTP {e.response.status_code}: {e}") from e
```

**Bad: Generic exception catching**
```python
try:
    response = requests.get(...)
except Exception:
    pass  # DON'T DO THIS - hides errors from caller
```

### Retry Logic

**Implement in CyperfApiClient (optional):**
```python
def get_all_attack_profiles(self, retries: int = 0) -> list[dict]:
    """With internal retry logic (optional)."""
    try:
        return self._fetch_profiles()
    except ConnectionError as e:
        if retries < 3:
            time.sleep(2 ** retries)  # Exponential backoff
            return self.get_all_attack_profiles(retries=retries + 1)
        raise
```

**OR rely on sync service for retries (recommended):**
The sync service (`perform_sync()`) handles all retry logic. Don't add retries
in the wrapper to avoid double-retry behavior.

### Timeout Settings

**Recommended timeouts:**
- Connection timeout: 10 seconds
- Read timeout: 30 seconds
- Total request timeout: 60 seconds

```python
session = requests.Session()
session.timeout = (10, 30)  # (connect, read)
```

### Certificate Handling

**Production:**
```python
# Verify SSL certificates
client = CyperfApiClient(
    controller_address="52.32.20.150",
    username="admin",
    password="...",
    verify_ssl=True  # Default
)
```

**Testing (if using self-signed certificates):**
```python
# Disable SSL verification (testing only!)
client = CyperfApiClient(
    controller_address="52.32.20.150",
    username="admin",
    password="...",
    verify_ssl=False
)

# Suppress InsecureRequestWarning
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

### Connection Pooling

**Implement session pooling for efficiency:**
```python
import requests

class CyperfApiClient:
    def __init__(self, ...):
        self.session = requests.Session()
        # Enable keep-alive for connection reuse
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10
        )
        self.session.mount('https://', adapter)
        self.session.auth = (username, password)
```

---

## Testing the Wrapper

### Unit Test Template

```python
import pytest
from cyperf_api_wrapper import CyperfApiClient
from unittest.mock import patch, MagicMock

class TestCyperfApiClient:

    def test_init_with_valid_credentials(self):
        """Test successful initialization."""
        with patch('cyperf_api_wrapper.requests.Session.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_get.return_value = mock_response

            client = CyperfApiClient(
                controller_address="52.32.20.150",
                username="admin",
                password="test"
            )
            assert client is not None

    def test_get_all_attack_profiles_success(self):
        """Test successful profile fetch."""
        with patch('cyperf_api_wrapper.requests.Session.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "attack_profiles": [
                    {
                        "id": "profile-1",
                        "name": "Apache-Log4j-RCE",
                        "cves": ["CVE-2021-44228"]
                    }
                ]
            }
            mock_get.return_value = mock_response

            client = CyperfApiClient(...)
            profiles = client.get_all_attack_profiles()

            assert len(profiles) == 1
            assert profiles[0]["name"] == "Apache-Log4j-RCE"

    def test_get_profiles_handles_connection_error(self):
        """Test connection error handling."""
        with patch('cyperf_api_wrapper.requests.Session.get') as mock_get:
            mock_get.side_effect = ConnectionError("Connection refused")

            client = CyperfApiClient(...)

            with pytest.raises(ConnectionError):
                client.get_all_attack_profiles()

    def test_get_profiles_handles_auth_error(self):
        """Test authentication error handling."""
        with patch('cyperf_api_wrapper.requests.Session.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_get.return_value = mock_response

            client = CyperfApiClient(...)

            with pytest.raises(Exception) as exc_info:
                client.get_all_attack_profiles()

            assert "401" in str(exc_info.value) or "unauthorized" in str(exc_info.value).lower()
```

### Integration Test Template

```python
# Test against real Cyperf Controller (staging environment only)
import pytest
from cyperf_api_wrapper import CyperfApiClient

@pytest.mark.integration
def test_real_cyperf_controller():
    """Test against real Cyperf Controller (requires credentials)."""
    client = CyperfApiClient(
        controller_address="52.32.20.150",
        username="admin",
        password="CyPerf&Keysight#1"  # From environment or fixture
    )

    profiles = client.get_all_attack_profiles()

    # Verify response structure
    assert isinstance(profiles, list)
    assert len(profiles) > 0

    for profile in profiles:
        assert "id" in profile
        assert "name" in profile
        assert "cves" in profile or ("metadata" in profile and "cves" in profile["metadata"])

    client.close()
```

---

## Version Notes

### Compatibility Matrix

| cyperf-api-wrapper | Cyperf Controller | Python | Requests |
|---|---|---|---|
| 1.0.x | 20.x-22.x | 3.10+ | 2.28+ |
| 1.1.x | 22.x-23.x | 3.11+ | 2.28+ |
| 2.0.x | 23.x+ | 3.12+ | 2.31+ |

### Changelog

**v2.0.0 (current)**
- Support for Cyperf 23.x+
- Python 3.12+ required
- Added `verify_ssl` parameter

**v1.1.0**
- Support for Cyperf 22.x-23.x
- Added pagination support
- Added timeout configuration

**v1.0.0**
- Initial release
- Basic profile fetching

---

## FAQ

**Q: What if Cyperf Controller API changes?**

A: Update cyperf-api-wrapper version. The sync service will continue to work
   as long as `get_all_attack_profiles()` returns the same schema.

**Q: Can I use the wrapper with multiple controllers?**

A: Yes. Create separate client instances for each controller:
```python
client_1 = CyperfApiClient("52.32.20.150", "admin", "pass1")
client_2 = CyperfApiClient("10.0.0.5", "admin", "pass2")
```

**Q: How do I handle self-signed certificates?**

A: Use `verify_ssl=False` in __init__() (testing only):
```python
client = CyperfApiClient(..., verify_ssl=False)
```

**Q: Does the wrapper cache profiles?**

A: No. It always fetches fresh data. The sync service handles caching
   by storing profiles in the database.

---

## Support & Documentation

- **Source Code:** [GitHub](https://github.com/keysight/cyperf-api-wrapper)
- **Issues:** Report bugs on GitHub Issues
- **Docs:** Full API documentation in package README
- **License:** Apache 2.0 (assumed; adjust as needed)

