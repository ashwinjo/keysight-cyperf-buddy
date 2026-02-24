import cyperf
import sys
import time
from typing import Optional

from fastapi import FastAPI
import uvicorn

import os
import json

CVE_STRIKES_FILE = "cve_strikes.json"
BATCH_SIZE = 500

configuration = cyperf.Configuration(
    host="https://52.32.20.150",
    username="admin",
    password="CyPerf&Keysight#1",
)
configuration.verify_ssl = False


def fetch_cve_strikes(skip: int = 0) -> dict:
    """
    Fetch all strikes from the API, extract CVE->Strike mapping, and return with profiling.
    """
    if os.path.exists(CVE_STRIKES_FILE):
        os.remove(CVE_STRIKES_FILE)

    cve_to_strike = {}
    batch_timings = []
    total_start = time.perf_counter()
    total_records = 0

    with cyperf.ApiClient(configuration) as api_client:
        api_instance = cyperf.ApplicationResourcesApi(api_client)
        take = BATCH_SIZE

        try:
            while True:
                batch_start = time.perf_counter()
                api_response = api_instance.get_resources_strikes(take=take, skip=skip)
                data_dict = json.loads(api_response.to_json()).get("data", [])
                batch_elapsed = time.perf_counter() - batch_start

                if len(data_dict) == 0:
                    break

                for strike in data_dict:
                    name = strike.get("Name", "N/A")
                    refs = strike.get("Metadata", {}).get("References", [])
                    cves = [
                        f"CVE-{r.get('Value')}"
                        for r in refs
                        if r.get("Type") == "CVE" and r.get("Value")
                    ]
                    for cve in cves:
                        cve_to_strike[cve] = name

                total_records += len(data_dict)
                batch_timings.append(
                    {
                        "skip": skip,
                        "count": len(data_dict),
                        "elapsed_sec": round(batch_elapsed, 3),
                    }
                )

                with open(CVE_STRIKES_FILE, "w") as f:
                    json.dump(cve_to_strike, f, indent=2)

                skip += BATCH_SIZE

        except Exception as e:
            total_elapsed = time.perf_counter() - total_start
            return {
                "success": False,
                "error": str(e),
                "cve_to_strike": cve_to_strike,
                "profiling": {
                    "total_elapsed_sec": round(total_elapsed, 3),
                    "batches_processed": len(batch_timings),
                    "total_records": total_records,
                    "total_cves": len(cve_to_strike),
                    "batch_timings": batch_timings,
                },
            }

    total_elapsed = time.perf_counter() - total_start
    return {
        "success": True,
        "cve_to_strike": cve_to_strike,
        "profiling": {
            "total_elapsed_sec": round(total_elapsed, 3),
            "batches_processed": len(batch_timings),
            "total_records": total_records,
            "total_cves": len(cve_to_strike),
            "batch_timings": batch_timings,
        },
    }


app = FastAPI(title="CVE Strikes Fetcher")


@app.post("/fetch-cve-strikes")
def fetch_cve_strikes_endpoint(
    skip: Optional[int] = 0, include_data: Optional[bool] = False
):
    """
    Fetch all strikes, extract CVE mappings, and return with time profiling.
    Set include_data=true to include full CVE mapping in response (can be large).
    """
    result = fetch_cve_strikes(skip=skip)
    if not include_data:
        result.pop("cve_to_strike", None)
        result["output_file"] = CVE_STRIKES_FILE
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        skip = int(sys.argv[1]) if len(sys.argv) > 1 else 0
        result = fetch_cve_strikes(skip=skip)
        print(json.dumps(result["profiling"], indent=2))
        if not result["success"]:
            sys.exit(1)
