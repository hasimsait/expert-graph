import os
from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.db.repository import GraphRepository, get_graph_repository
from app.module_c_mcp.retrieval import fetch_approved_facts

router = APIRouter(tags=["MCP UI Widget"])

# Setup Jinja2 templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def get_available_concepts(repo: GraphRepository):
    """Fetch distinct concept names that actually have approved facts in the Data-Graph."""
    approved_facts = repo.get_approved_facts("ALL")
    active_concepts = set()
    for fact in approved_facts:
        rel = fact.get("relation")
        if rel:
            active_concepts.add(rel.upper())
    return sorted(list(active_concepts))

@router.get("/ui/facts-widget", response_class=HTMLResponse)
def render_facts_widget(
    request: Request,
    concept: str = Query("ALL"),
    repo: GraphRepository = Depends(get_graph_repository)
):
    """Dynamic Jinja2 HTML widget compliant with mcp-ui standard."""
    active_concept = concept.strip() if concept else "ALL"
    facts = fetch_approved_facts(active_concept, repo=repo)
    available_concepts = get_available_concepts(repo)
    
    return templates.TemplateResponse(
        request=request,
        name="facts_widget.html",
        context={
            "concept": active_concept,
            "facts": facts,
            "available_concepts": available_concepts
        }
    )
