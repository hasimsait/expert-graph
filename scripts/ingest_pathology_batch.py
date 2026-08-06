import sys
import os
import json
import asyncio
import httpx
import time
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings

# Sample Pathology Reports Batch Dataset
SAMPLE_PATHOLOGY_BATCH = [
    {
        "chunk_id": "PATH_REPORT_001",
        "text": "SPECIMEN: Breast core biopsy (Right breast). DIAGNOSIS: Invasive Ductal Carcinoma, Grade 3. BIOMARKERS: Tumor overexpresses HER2 receptor (3+ IHC score). Estrogen Receptor is positive in 85% of tumor nuclei."
    },
    {
        "chunk_id": "PATH_REPORT_002",
        "text": "SPECIMEN: Right lung upper lobe wedge resection. DIAGNOSIS: Non-Small Cell Lung Adenocarcinoma. GENETICS: Molecular testing positive for EGFR L858R exon 21 mutation. ALK translocation negative."
    },
    {
        "chunk_id": "PATH_REPORT_003",
        "text": "SPECIMEN: Thyroid fine needle aspiration. DIAGNOSIS: Papillary Thyroid Carcinoma. GENETICS: BRAF V600E point mutation identified by NGS. Surgical margins recommended."
    },
    {
        "chunk_id": "PATH_REPORT_004",
        "text": "SPECIMEN: Colon endoscopic biopsy. DIAGNOSIS: Colorectal Adenocarcinoma, moderately differentiated. BIOMARKERS: KRAS wild-type, NRAS wild-type, Microsatellite Instability High (MSI-H)."
    },
    {
        "chunk_id": "PATH_REPORT_005",
        "text": "SPECIMEN: Skin punch biopsy (Left forearm). DIAGNOSIS: Cutaneous Malignant Melanoma, Nodular subtype. Breslow thickness: 2.1mm. GENETICS: BRAF V600K mutation positive."
    }
]

async def ingest_single_report(client: httpx.AsyncClient, report: Dict[str, Any], server_url: str) -> Dict[str, Any]:
    url = f"{server_url}/api/ingest"
    payload = {
        "chunk_id": report["chunk_id"],
        "text": report["text"]
    }
    start_time = time.time()
    try:
        response = await client.post(url, json=payload, timeout=60.0)
        elapsed = time.time() - start_time
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ [{report['chunk_id']}] Ingested {data.get('triples_ingested', 0)} candidate triple(s) in {elapsed:.2f}s")
            return data
        else:
            print(f"  ! [{report['chunk_id']}] Error HTTP {response.status_code}: {response.text}")
            return {"chunk_id": report["chunk_id"], "error": response.text}
    except Exception as e:
        print(f"  ! [{report['chunk_id']}] Ingestion failed: {e}")
        return {"chunk_id": report["chunk_id"], "error": str(e)}

async def run_batch_ingestion(server_url: str = settings.BASE_URL, batch_file: str = None, concurrency: int = 3):
    print("\n=======================================================")
    print("      EXPERTGRAPH PATHOLOGY BATCH INGESTION PIPELINE")
    print("=======================================================\n")

    reports = SAMPLE_PATHOLOGY_BATCH
    if batch_file and os.path.exists(batch_file):
        with open(batch_file, "r") as f:
            reports = json.load(f)
        print(f"--> Loaded {len(reports)} custom pathology reports from: {batch_file}")
    else:
        print(f"--> Loading default sample pathology batch ({len(reports)} reports)")

    print(f"--> Target Server:  {server_url}")
    print(f"--> Concurrency:    {concurrency} worker(s)\n")

    semaphore = asyncio.Semaphore(concurrency)

    async def worker(client: httpx.AsyncClient, report: Dict[str, Any]):
        async with semaphore:
            return await ingest_single_report(client, report, server_url)

    start_batch = time.time()
    async with httpx.AsyncClient() as client:
        tasks = [worker(client, r) for r in reports]
        results = await asyncio.gather(*tasks)

    total_elapsed = time.time() - start_batch
    total_triples = sum(r.get("triples_ingested", 0) for r in results if "triples_ingested" in r)

    print("\n=======================================================")
    print("  BATCH INGESTION COMPLETE")
    print("=======================================================")
    print(f"  • Reports Processed:  {len(reports)}")
    print(f"  • Triples Extracted:  {total_triples}")
    print(f"  • Total Time Taken:   {total_elapsed:.2f} seconds")
    print("=======================================================")
    print("Next Steps:")
    print("  1. Open Annotator Dashboard: http://localhost:8000/")
    print("  2. Review & Approve candidate pathology edges into Ground Truth")
    print("=======================================================\n")

if __name__ == "__main__":
    server = sys.argv[1] if len(sys.argv) > 1 else settings.BASE_URL
    file_path = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(run_batch_ingestion(server_url=server, batch_file=file_path))
