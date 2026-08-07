import sys
import os
import json
import logging
import asyncio
import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.db.ontology_loader import load_custom_ontology_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_pathology_flow")

SAMPLE_PATHOLOGY_CHUNKS = [
    {
        "chunk_id": "PATH_TEST_001",
        "text": "SPECIMEN: Breast tissue core biopsy. DIAGNOSIS: Invasive Ductal Carcinoma, Grade 3. BIOMARKERS: Overexpresses HER2 receptor (3+ IHC score)."
    },
    {
        "chunk_id": "PATH_TEST_002",
        "text": "SPECIMEN: Right lung lobe resection. DIAGNOSIS: Non-Small Cell Lung Adenocarcinoma. GENETICS: EGFR L858R mutation detected."
    },
    {
        "chunk_id": "PATH_TEST_003",
        "text": "SPECIMEN: Thyroid fine needle aspiration. DIAGNOSIS: Papillary Thyroid Carcinoma. BIOMARKERS: BRAF V600E mutation identified."
    }
]

async def run_pathology_flow(server_url:str = "http://localhost:8000"):
    print("\n========================================================================")
    print("      EXPERTGRAPH PATHOLOGY SIEVE & GROUND TRUTH TEST FLOW")
    print("========================================================================\n")

    print(f"--> LLM Provider Configuration:")
    print(f"    • Provider: {settings.LLM_PROVIDER}")
    print(f"    • Model:    {settings.LLM_MODEL}")
    print(f"    • Endpoint: {settings.LLM_BASE_URL if settings.LLM_PROVIDER != 'openai' else 'OpenAI Cloud'}")
    print(f"    • Max Tokens: {settings.MAX_TOKENS}\n")

    async with httpx.AsyncClient(base_url=server_url,timeout=120.0) as client:
        # Step 1: Reset Database & Queue State
        print("Step 1: Resetting Database & Queue State...")
        reset_res = await client.post("/api/reset")
        assert reset_res.status_code == 200
        print("  ✓ Database & Queue reset cleanly.\n")
        # Step 2: Load Medical Ontology Domain Baseline
        print("Step 2: Loading Medical Ontology Domain Baseline into Meta-Graph...")
        sample_json_path = os.path.join(os.path.dirname(__file__), "sample_medical_ontology.json")
        if os.path.exists(sample_json_path):
            ont_res = await load_custom_ontology_json(sample_json_path)
            print(f"  ✓ Loaded Medical Ontology: {ont_res['concepts_loaded']} concepts, {ont_res['relationships_loaded']} meta-relationships.\n")

        # Step 3: Ingest Pathology Chunks through Sieve API
        print("Step 3: Ingesting Pathology Reports through Sieve (Extractor -> Critic -> Graph)...")
        total_triples = 0
        for chunk in SAMPLE_PATHOLOGY_CHUNKS:
            res = await client.post("/api/ingest", json={"chunk_id": chunk["chunk_id"], "text": chunk["text"]})
            assert res.status_code == 200
            count = res.json()["triples_ingested"]
            total_triples += count
            print(f"  ✓ Report '{chunk['chunk_id']}' ingested: {count} candidate triple(s) pushed to pending queue.")

        print(f"\n  ✓ Total Candidate Triples Ingested: {total_triples}\n")

        # Step 4: Fetch Pending Queue
        print("Step 4: Fetching Pending Queue for Pathologist Annotation ('/api/queue')...")
        queue_res = await client.get("/api/queue?limit=20")
        assert queue_res.status_code == 200
        queue = queue_res.json()["queue"]
        print(f"  ✓ Pending Queue Count: {len(queue)} candidate edges awaiting approval.\n")

        print("--- PENDING PATHOLOGY CANDIDATE EDGES ---")
        for i, edge in enumerate(queue, 1):
            subj = edge['subject']['name']
            rel = edge['relation']
            obj = edge['object']['name']
            meta_concept = edge.get('meta_concept', 'MEDICAL_CONDITION')
            mapping_type = edge.get('meta_mapping', 'SUBCLASS_OF')
            print(f" [{i}] Edge ID: {edge['edge_id']}")
            print(f"     Candidate Fact: ({subj}) -[{rel}]-> ({obj})")
            print(f"     Meta Mapping:   {rel} -[{mapping_type}]-> {meta_concept}")
            print(f"     Source Text:    \"{edge['chunk_text'][:80]}...\"\n")

        # Step 5: Simulate Pathologist Approvals
        print("Step 5: Simulating Pathologist Approvals ('/api/approve')...")
        for edge in queue:
            app_res = await client.post(f"/api/approve/{edge['edge_id']}", json={"user_id": "Dr_Pathologist_Smith"})
            assert app_res.status_code == 200
            print(f"  ✓ Edge '{edge['edge_id']}' approved by Dr_Pathologist_Smith.")

        # Step 6: Verify Live Stats
        print("\nStep 6: Checking Live Stats ('/api/stats')...")
        stats_res = await client.get("/api/stats")
        assert stats_res.status_code == 200
        stats = stats_res.json()
        print(f"  ✓ Live Stats -> Pending: {stats['pending']} | Approved: {stats['approved']} | Rejected: {stats['rejected']}\n")

        # Step 7: Test Dynamic RAG Widget Rendering
        print("Step 7: Testing Dynamic RAG Widget Rendering ('/ui/facts-widget')...")
        widget_res = await client.get("/ui/facts-widget?concept=MEDICAL_CONDITION")
        assert widget_res.status_code == 200
        print("  ✓ Dynamic MCP-UI Widget generated successfully for MEDICAL_CONDITION query.")

    print("\n========================================================================")
    print("  PATHOLOGY SIEVE & GROUND TRUTH TEST COMPLETED SUCCESSFULLY!")
    print("========================================================================")
    print("To view these approved pathology facts in the UI:")
    print("  1. Run Server: PYTHONPATH=. uvicorn app.main:app --port 8000")
    print("  2. Annotator Dashboard: http://localhost:8000/")
    print("  3. RAG Facts Widget:    http://localhost:8000/ui/facts-widget")
    print("========================================================================\n")

if __name__ == "__main__":
    server = sys.argv[1] if len(sys.argv)>1 else "http://localhost:8000"
    asyncio.run(run_pathology_flow(server))
