import pytest
import asyncio
from app.main import container
from app.db.neo4j_client import run_cypher, Neo4jConnection
from app.module_c_mcp.retrieval import fetch_approved_facts

pytestmark = pytest.mark.integration

async def _setup_test_db():
    Neo4jConnection._driver = None
    try:
        await run_cypher("MATCH (n:TestNode) DETACH DELETE n")
    except Exception:
        pass

    seed_cypher = """
    // 1. PATH_TEST_002
    CREATE (e1:Entity:TestNode {name: 'Test_Non-Small Cell Lung Adenocarcinoma', type: 'DISEASE'})
    CREATE (e2:Entity:TestNode {name: 'Test_EGFR L858R mutation', type: 'GENETICS'})
    CREATE (e1)-[:HAS_GENETICS {status: 'approved', confidence: 1.0, chunk_id: 'PATH_TEST_002', chunk_text: 'SPECIMEN: Right lung lobe resection. DIAGNOSIS: Non-Small Cell Lung Adenocarcinoma. GENETICS: EGFR L858R mutation detected.', edge_id: 'test_edge_1'}]->(e2)

    CREATE (e3:Entity:TestNode {name: 'Test_Right lung lobe resection', type: 'SPECIMEN'})
    CREATE (e3)-[:HAS_DIAGNOSIS {status: 'approved', confidence: 1.0, chunk_id: 'PATH_TEST_002', chunk_text: 'SPECIMEN: Right lung lobe resection. DIAGNOSIS: Non-Small Cell Lung Adenocarcinoma. GENETICS: EGFR L858R mutation detected.', edge_id: 'test_edge_2'}]->(e1)

    // 2. PATH_TEST_003
    CREATE (e4:Entity:TestNode {name: 'Test_Thyroid fine needle aspiration', type: 'SPECIMEN'})
    CREATE (e5:Entity:TestNode {name: 'Test_Papillary Thyroid Carcinoma', type: 'DISEASE'})
    CREATE (e4)-[:HAS_DIAGNOSIS {status: 'approved', confidence: 1.0, chunk_id: 'PATH_TEST_003', chunk_text: 'SPECIMEN: Thyroid fine needle aspiration. DIAGNOSIS: Papillary Thyroid Carcinoma. BIOMARKERS: BRAF V600E mutation identified.', edge_id: 'test_edge_3'}]->(e5)

    CREATE (e6:Entity:TestNode {name: 'Test_BRAF V600E mutation', type: 'BIOMARKER'})
    CREATE (e5)-[:HAS_BIOMARKER {status: 'approved', confidence: 1.0, chunk_id: 'PATH_TEST_003', chunk_text: 'SPECIMEN: Thyroid fine needle aspiration. DIAGNOSIS: Papillary Thyroid Carcinoma. BIOMARKERS: BRAF V600E mutation identified.', edge_id: 'test_edge_4'}]->(e6)

    // 3. PATH_TEST_001
    CREATE (e7:Entity:TestNode {name: 'Test_Breast tissue core biopsy', type: 'SPECIMEN'})
    CREATE (e8:Entity:TestNode {name: 'Test_HER2 receptor', type: 'BIOMARKER'})
    CREATE (e7)-[:EXPRESSES {status: 'pending', confidence: 1.0, chunk_id: 'PATH_TEST_001', chunk_text: 'SPECIMEN: Breast tissue core biopsy. DIAGNOSIS: Invasive Ductal Carcinoma, Grade 3. BIOMARKERS: Overexpresses HER2 receptor (3+ IHC score).', edge_id: 'test_edge_5'}]->(e8)
    CREATE (e7)-[:HAS_BIOMARKER {status: 'approved', confidence: 1.0, chunk_id: 'PATH_TEST_001', chunk_text: 'SPECIMEN: Breast tissue core biopsy. DIAGNOSIS: Invasive Ductal Carcinoma, Grade 3. BIOMARKERS: Overexpresses HER2 receptor (3+ IHC score).', edge_id: 'test_edge_6'}]->(e8)

    CREATE (e9:Entity:TestNode {name: 'Test_Invasive Ductal Carcinoma', type: 'DISEASE'})
    CREATE (e7)-[:HAS_DIAGNOSIS {status: 'approved', confidence: 1.0, chunk_id: 'PATH_TEST_001', chunk_text: 'SPECIMEN: Breast tissue core biopsy. DIAGNOSIS: Invasive Ductal Carcinoma, Grade 3. BIOMARKERS: Overexpresses HER2 receptor (3+ IHC score).', edge_id: 'test_edge_7'}]->(e9)

    CREATE (e10:Entity:TestNode {name: 'Test_3', type: 'GRADE'})
    CREATE (e9)-[:HAS_GRADE {status: 'approved', confidence: 1.0, chunk_id: 'PATH_TEST_001', chunk_text: 'SPECIMEN: Breast tissue core biopsy. DIAGNOSIS: Invasive Ductal Carcinoma, Grade 3. BIOMARKERS: Overexpresses HER2 receptor (3+ IHC score).', edge_id: 'test_edge_8'}]->(e10)
    """
    try:
        await run_cypher(seed_cypher)
        await Neo4jConnection.reset_driver()
    except Exception as e:
        print(f"Failed to seed db: {e}")
    finally:
        Neo4jConnection._driver = None

async def _teardown_test_db():
    Neo4jConnection._driver = None
    try:
        await run_cypher("MATCH (n:TestNode) DETACH DELETE n")
        await Neo4jConnection.reset_driver()
    except Exception:
        pass
    finally:
        Neo4jConnection._driver = None

def setup_module(module):
    """Seed Neo4j database with test facts and warmup the TF-IDF engine."""
    asyncio.run(_setup_test_db())

def teardown_module(module):
    """Clean up test nodes after tests finish."""
    asyncio.run(_teardown_test_db())

@pytest.mark.anyio
async def test_mcp_rag_breast_cancer_query():
    """Test the complete RAG MCP extraction pipeline against the live database without LLMs."""
    
    # 1. Start with an empty TF-IDF cache
    search_service = container.search_service()
    search_service.reset_cache()
    repo = container.edge_repo()

    # 2. Before approval, search for breast cancer. The pending 'test_edge_5' should NOT be returned.
    query = "What genetic mutations were identified in breast cancer tissue samples?"
    facts_before = await fetch_approved_facts(query=query)
    
    # The HAS_BIOMARKER edge (test_edge_6) is approved, so it might be found, but test_edge_5 should NOT be there.
    edge_5_before = [f for f in facts_before if f.get("edge_id") == "test_edge_5"]
    assert len(edge_5_before) == 0

    # 3. Simulate the user approving the fact in the UI Dashboard!
    # This calls get_search_service().add_fact_delta() internally, testing our vocabulary expansion fix!
    await repo.update_edge_status("test_edge_5", "approved", "Dr_Test_Pathologist")

    # 4. Search again exactly what the user queried in the UI / MCP
    facts_after = await fetch_approved_facts(query=query)
    
    # We expect to find the facts related to breast cancer / HER2
    assert len(facts_after) >= 1
    
    # Let's verify that the newly approved fact is now returned!
    edge_5_after = [f for f in facts_after if f.get("edge_id") == "test_edge_5"]
    assert len(edge_5_after) >= 1
    assert edge_5_after[0]["object"] == "Test_HER2 receptor"
