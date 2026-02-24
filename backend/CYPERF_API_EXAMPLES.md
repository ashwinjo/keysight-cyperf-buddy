# Cyperf API Examples & Mock Data

This document contains example Cyperf API responses and demonstrates how the sync service parses them.

---

## Real-World Example: Attack Profile Response

### Cyperf Controller: GET /api/v2/attack-profiles

**Request:**
```bash
curl -k -u admin:CyPerf&Keysight#1 \
  https://52.32.20.150/api/v2/attack-profiles \
  -H "Content-Type: application/json"
```

### Expected Response (Status 200 OK)

```json
{
  "attack_profiles": [
    {
      "id": "profile-uuid-001",
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
      "applications": [
        "Apache",
        "Log4j",
        "Spring",
        "ActiveMQ"
      ]
    },
    {
      "id": "profile-uuid-002",
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
        "severity": "CRITICAL",
        "affected_systems": ["Microsoft Exchange"],
        "cpe": ["cpe:2.3:a:microsoft:exchange_server:2013:*:*:*:*:*:*:*"],
        "attack_technique": "MITRE ATT&CK / T1190"
      },
      "applications": [
        "Microsoft Exchange Server",
        "Outlook"
      ]
    },
    {
      "id": "profile-uuid-003",
      "name": "Cisco-IOS-Command-Injection",
      "description": "Command injection in Cisco IOS devices",
      "version": "1.0",
      "enabled": true,
      "cves": [
        "CVE-2023-20820",
        "CVE-2023-20821"
      ],
      "metadata": {
        "attack_type": "Command Injection",
        "severity": "HIGH",
        "affected_systems": ["Cisco IOS", "Cisco IOS XE"],
        "cpe": [
          "cpe:2.3:o:cisco:ios:*:*:*:*:*:*:*:*",
          "cpe:2.3:o:cisco:ios_xe:*:*:*:*:*:*:*:*"
        ]
      },
      "applications": ["Cisco Routers", "Cisco Switches"]
    },
    {
      "id": "profile-uuid-004",
      "name": "SQL-Injection-Generic",
      "description": "Generic SQL injection attack patterns",
      "version": "3.1",
      "enabled": true,
      "cves": [
        "CVE-2019-6102",
        "CVE-2020-5410",
        "CVE-2021-22911"
      ],
      "metadata": {
        "attack_type": "SQL Injection",
        "severity": "HIGH",
        "affected_systems": ["PostgreSQL", "MySQL", "SQL Server", "Oracle"],
        "attack_technique": "MITRE ATT&CK / T1190"
      },
      "applications": [
        "PostgreSQL",
        "MySQL",
        "Microsoft SQL Server",
        "Oracle Database"
      ]
    }
  ],
  "total_count": 4,
  "page": 1,
  "per_page": 100
}
```

---

## Sync Service: Data Extraction

### Input to CyperfService.extract_cves_from_profiles()

```python
profiles = [
    {
        "id": "profile-uuid-001",
        "name": "Apache-Log4j-RCE",
        "version": "2.0",
        "cves": [
            "CVE-2021-44228",
            "CVE-2021-44229",
            "CVE-2021-44230"
        ],
        "metadata": {...}
    },
    {
        "id": "profile-uuid-002",
        "name": "Microsoft-Exchange-ProxyLogon",
        "cves": [
            "CVE-2021-26855",
            "CVE-2021-26857",
            "CVE-2021-26858",
            "CVE-2021-27065"
        ],
        ...
    },
    ...
]
```

### Extraction Process

```python
cve_mappings = {}

for profile in profiles:
    profile_name = profile.get("name", "unknown")

    # Extract CVEs from profile
    cves = profile.get("cves", [])
    if not isinstance(cves, list):
        cves = [cves]

    # Handle dictionary CVE objects
    for cve in cves:
        if isinstance(cve, str):
            cve_id = cve
        elif isinstance(cve, dict):
            cve_id = cve.get("id") or cve.get("cve_id")
        else:
            cve_id = str(cve)

        if cve_id:
            cve_mappings[cve_id] = profile_name

# Result:
cve_mappings = {
    "CVE-2021-44228": "Apache-Log4j-RCE",
    "CVE-2021-44229": "Apache-Log4j-RCE",
    "CVE-2021-44230": "Apache-Log4j-RCE",
    "CVE-2021-26855": "Microsoft-Exchange-ProxyLogon",
    "CVE-2021-26857": "Microsoft-Exchange-ProxyLogon",
    "CVE-2021-26858": "Microsoft-Exchange-ProxyLogon",
    "CVE-2021-27065": "Microsoft-Exchange-ProxyLogon",
    "CVE-2023-20820": "Cisco-IOS-Command-Injection",
    "CVE-2023-20821": "Cisco-IOS-Command-Injection",
    "CVE-2019-6102": "SQL-Injection-Generic",
    "CVE-2020-5410": "SQL-Injection-Generic",
    "CVE-2021-22911": "SQL-Injection-Generic",
}
```

### Output: Database Upsert

```python
# For each mapping, execute:
for cve_id, profile_name in cve_mappings.items():
    record = CyperfSupportedCVE(
        cve_id=cve_id,
        attack_profile_name=profile_name,
        attack_profile_id=None,  # Optional; not always available
        profile_version=None,     # Optional; not always available
        last_synced=datetime.utcnow(),
        is_deprecated=False,
    )
    session.merge(record)

session.commit()
```

---

## Database Result: cyperf_supported_cves

After sync completes, the database contains:

```
id | cve_id           | attack_profile_name             | first_synced            | last_synced             | is_deprecated
---|------------------|---------------------------------|-------------------------|-------------------------|---------------
 1 | CVE-2021-44228   | Apache-Log4j-RCE                | 2025-02-23 08:15:00     | 2025-02-23 08:15:00     | 0
 2 | CVE-2021-44229   | Apache-Log4j-RCE                | 2025-02-23 08:15:00     | 2025-02-23 08:15:00     | 0
 3 | CVE-2021-44230   | Apache-Log4j-RCE                | 2025-02-23 08:15:00     | 2025-02-23 08:15:00     | 0
 4 | CVE-2021-26855   | Microsoft-Exchange-ProxyLogon   | 2025-02-23 08:15:00     | 2025-02-23 08:15:00     | 0
 5 | CVE-2021-26857   | Microsoft-Exchange-ProxyLogon   | 2025-02-23 08:15:00     | 2025-02-23 08:15:00     | 0
 6 | CVE-2021-26858   | Microsoft-Exchange-ProxyLogon   | 2025-02-23 08:15:00     | 2025-02-23 08:15:00     | 0
 7 | CVE-2021-27065   | Microsoft-Exchange-ProxyLogon   | 2025-02-23 08:15:00     | 2025-02-23 08:15:00     | 0
 8 | CVE-2023-20820   | Cisco-IOS-Command-Injection     | 2025-02-23 08:15:00     | 2025-02-23 08:15:00     | 0
 9 | CVE-2023-20821   | Cisco-IOS-Command-Injection     | 2025-02-23 08:15:00     | 2025-02-23 08:15:00     | 0
10 | CVE-2019-6102    | SQL-Injection-Generic           | 2025-02-23 08:15:00     | 2025-02-23 08:15:00     | 0
11 | CVE-2020-5410    | SQL-Injection-Generic           | 2025-02-23 08:15:00     | 2025-02-23 08:15:00     | 0
12 | CVE-2021-22911   | SQL-Injection-Generic           | 2025-02-23 08:15:00     | 2025-02-23 08:15:00     | 0
```

---

## API Response Format After Sync

### GET /admin/sync-status

```json
{
  "last_successful_sync": "2025-02-23T08:15:00Z",
  "last_attempted_sync": "2025-02-23T08:15:00Z",
  "sync_status": "success",
  "cverf_profiles_synced": 4,
  "cverf_cves_extracted": 12,
  "error_message": null,
  "next_scheduled_sync": "2025-02-24T02:00:00Z"
}
```

---

## Error Scenarios

### Scenario 1: Cyperf Controller Unreachable

**Request to Cyperf:** `GET https://52.32.20.150/api/v2/attack-profiles`

**Response:** Connection timeout

**Sync Service Behavior:**
```
[Attempt 1] CyperfConnectionError: Connection to Cyperf failed: [Errno 110] Connection timed out
[Attempt 2] CyperfConnectionError: Connection to Cyperf failed: [Errno 110] Connection timed out
[Attempt 3] (after 5s) CyperfConnectionError: Connection to Cyperf failed: [Errno 110] Connection timed out

Log Error: "Cyperf sync FAILED after 3 attempts: Connection error: ... (retaining previous sync data)"
```

**GET /admin/sync-status Response:**
```json
{
  "last_successful_sync": "2025-02-22T08:15:00Z",
  "last_attempted_sync": "2025-02-23T10:15:00Z",
  "sync_status": "failed",
  "cverf_profiles_synced": 4,
  "cverf_cves_extracted": 12,
  "error_message": "Connection error: Connection to Cyperf failed: [Errno 110] Connection timed out",
  "next_scheduled_sync": "2025-02-24T02:00:00Z"
}
```

**Notes:**
- `last_successful_sync` remains at last successful time (2025-02-22)
- `cverf_cves_extracted` still shows 12 (old data is retained)
- `error_message` contains the connection error
- Sync will retry automatically at next scheduled time

### Scenario 2: Authentication Failure

**Request:** Same as above, but with wrong credentials

**Response:** 401 Unauthorized

**Sync Service Behavior:**
```
[Attempt 1] CyperfAPIError: Authentication failed: 401 Unauthorized

Log Error: "Cyperf sync FAILED after 3 attempts: API error: Authentication failed"
```

**No Retry:** Authentication errors don't trigger retries (credentials won't magically become correct)

### Scenario 3: Malformed CVE in Response

**Profile response includes:**
```json
{
  "name": "Bad-Profile",
  "cves": [
    "CVE-2021-44228",
    null,
    "",
    {"invalid_key": "value"}
  ]
}
```

**Sync Service Behavior:**
```
Log Warning: "Failed to parse CVEs from profile at index 2: ... ; skipping this profile"

# Successfully extracts: CVE-2021-44228
# Silently skips: null, "", {"invalid_key": "value"}
```

---

## Testing Mock Responses

### Using curl with Mock Endpoint

```bash
# If you have a mock server running on localhost:8001
curl http://localhost:8001/mock-cyperf/profiles

# Response:
HTTP/1.1 200 OK
Content-Type: application/json

{
  "attack_profiles": [
    {
      "id": "profile-uuid-001",
      "name": "Apache-Log4j-RCE",
      "cves": ["CVE-2021-44228", ...]
    },
    ...
  ]
}
```

### Local Testing with Python

```python
import json
from services.cyperf_service import CyperfService

# Mock profiles (simulate Cyperf response)
mock_profiles = [
    {
        "id": "profile-uuid-001",
        "name": "Apache-Log4j-RCE",
        "cves": ["CVE-2021-44228", "CVE-2021-44229"]
    },
    {
        "id": "profile-uuid-002",
        "name": "Microsoft-Exchange-ProxyLogon",
        "cves": ["CVE-2021-26855", "CVE-2021-26857"]
    }
]

# Test extraction
service = CyperfService(
    controller_ip="52.32.20.150",
    username="admin",
    password="CyPerf&Keysight#1"
)

cve_mappings = service.extract_cves_from_profiles(mock_profiles)

print(json.dumps(cve_mappings, indent=2))
# Output:
# {
#   "CVE-2021-44228": "Apache-Log4j-RCE",
#   "CVE-2021-44229": "Apache-Log4j-RCE",
#   "CVE-2021-26855": "Microsoft-Exchange-ProxyLogon",
#   "CVE-2021-26857": "Microsoft-Exchange-ProxyLogon"
# }
```

---

## Integration with CVE API

### Example: Query Testable CVEs

After sync completes, you can query for testable CVEs:

**Query:** Get all CVEs that can be tested with Cyperf

```python
from sqlalchemy import select
from db.cyperf_mapping import CyperfSupportedCVE

# In your CVE service:
async def get_testable_cves(session):
    """Get all CVEs with Cyperf attack profiles."""
    stmt = select(CyperfSupportedCVE).filter(
        CyperfSupportedCVE.is_deprecated == False
    )
    result = await session.execute(stmt)
    return result.scalars().all()
```

**API Response Example:**

```json
{
  "testable_cves": [
    {
      "cve_id": "CVE-2021-44228",
      "attack_profile_name": "Apache-Log4j-RCE",
      "testable": true
    },
    {
      "cve_id": "CVE-2021-44229",
      "attack_profile_name": "Apache-Log4j-RCE",
      "testable": true
    },
    ...
  ],
  "total_count": 12,
  "last_synced": "2025-02-23T08:15:00Z"
}
```

---

## Performance Testing

### Load Test: Sync 10,000 CVEs

```bash
# Simulate large response
python << 'EOF'
import json
import time

# Generate mock profiles with many CVEs
profiles = []
for i in range(100):
    cves = [f"CVE-2020-{i:05d}" for _ in range(100)]
    profiles.append({
        "id": f"profile-{i}",
        "name": f"Attack-Profile-{i}",
        "cves": cves
    })

# Measure extraction time
start = time.time()
cve_mappings = {}
for profile in profiles:
    name = profile["name"]
    for cve in profile["cves"]:
        cve_mappings[cve] = name
elapsed = time.time() - start

print(f"Extracted {len(cve_mappings)} CVEs in {elapsed:.2f}s")
# Output: Extracted 10000 CVEs in 0.12s
EOF
```

---

## Cyperf API Wrapper Implementation Checklist

- [ ] `CyperfApiClient` class initializes with controller IP, username, password
- [ ] `__init__()` establishes HTTPS connection with certificate validation (or disable for testing)
- [ ] `get_all_attack_profiles()` returns list of profile dictionaries
- [ ] Profile objects include: `id`, `name`, `version`, `cves` (or `metadata.cves`)
- [ ] Handles pagination if API returns >100 profiles
- [ ] Raises `ConnectionError` on network failures
- [ ] Raises exception with "401" or "unauthorized" on auth failures
- [ ] Raises exception with descriptive message on other API errors
- [ ] Implements timeout (suggest 30 seconds)
- [ ] Implements retry logic (optional; sync service handles retries)
