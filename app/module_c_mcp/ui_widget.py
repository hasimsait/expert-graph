import os
from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dependency_injector.wiring import Provide, inject
from app.db.repository.edge_repo import EdgeRepository
from app.core.container import Container
from app.module_c_mcp import retrieval

router = APIRouter(tags=["MCP UI Widget"])

# Setup Jinja2 templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

async def get_available_concepts(repo: EdgeRepository):
    """Fetch distinct concept names that actually have approved facts in the Data-Graph asynchronously."""
    approved_facts = await repo.get_approved_facts()
    active_concepts = set()
    for fact in approved_facts:
        rel = fact.get("relation")
        if rel:
            active_concepts.add(rel.upper())
    return sorted(list(active_concepts))

@router.get("/ui/facts-widget", response_class=HTMLResponse)
@inject
async def render_facts_widget(
    request: Request,
    concept: str = Query("ALL"),
    repo: EdgeRepository = Depends(Provide[Container.edge_repo])
):
    """Dynamic Jinja2 HTML widget compliant with mcp-ui standard asynchronously."""
    active_concept = concept.strip() if concept else "ALL"
    facts = await retrieval.fetch_approved_facts(active_concept)
    available_concepts = await get_available_concepts(repo)
    
    return templates.TemplateResponse(
        request=request,
        name="facts_widget.html",
        context={
            "concept": active_concept,
            "facts": facts,
            "available_concepts": available_concepts
        }
    )
