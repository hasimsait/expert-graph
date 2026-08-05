import os
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.module_c_mcp.retrieval import fetch_approved_facts

from app.db.neo4j_client import run_cypher
from app.db.mock_graph import mock_graph_store

router = APIRouter(tags=["MCP UI Widget"])

# Setup Jinja2 templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def get_available_concepts():
    """Fetch distinct concept names that actually have approved facts in the Data-Graph."""
    cypher = """
    MATCH (s:Entity)-[r]->(o:Entity)
    WHERE r.status = "approved"
    OPTIONAL MATCH (c1:Concept {name: type(r)})-[m:SUBCLASS_OF|SYNONYM_OF*0..2]->(c2:Concept)
    RETURN DISTINCT coalesce(c2.name, type(r)) AS name
    ORDER BY name ASC
    """
    res = run_cypher(cypher)
    if res:
        concepts = [r["name"] for r in res if r.get("name")]
        if concepts:
            return concepts

    # Fallback to in-memory mock store concepts for approved facts
    active_concepts = set()
    for edge in mock_graph_store.edges:
        if edge.get("status") == "approved":
            rel = edge.get("relation", "").upper()
            meta_parent = mock_graph_store.meta_concepts.get(rel, {}).get("parent") or rel
            active_concepts.add(meta_parent)
            active_concepts.add(rel)
    return sorted(list(active_concepts))

@router.get("/ui/facts-widget", response_class=HTMLResponse)
def render_facts_widget(request: Request, concept: str = Query("ALL")):
    """Dynamic Jinja2 HTML widget compliant with mcp-ui standard."""
    active_concept = concept.strip() if concept else "ALL"
    facts = fetch_approved_facts(active_concept)
    available_concepts = get_available_concepts()
    
    return templates.TemplateResponse(
        request=request,
        name="facts_widget.html",
        context={
            "concept": active_concept,
            "facts": facts,
            "available_concepts": available_concepts
        }
    )
