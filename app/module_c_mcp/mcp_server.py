import json
import logging
from fastmcp import FastMCP
from app.config import settings
from app.module_c_mcp.retrieval import fetch_approved_facts

logger = logging.getLogger(__name__)

mcp_app = FastMCP("ExpertGraph-MCP-Server")

@mcp_app.tool()
async def retrieve_verified_facts(concept: str = "ALL", query: str = None) -> str:
    """
    Retrieves human-verified ground truth graph facts for a concept domain or query.
    Performs Meta-Graph subclass expansion to include child concepts.
    Returns facts JSON along with _meta.ui.resourceUri targeting the secure mcp-ui presentation widget.
    """
    target_concept = query or concept or "ALL"
    facts = fetch_approved_facts(target_concept)
    ui_resource_uri = f"{settings.BASE_URL}/ui/facts-widget?concept={target_concept}"
    
    payload = {
        "concept": concept,
        "verified_facts_count": len(facts),
        "facts": facts,
        "_meta": {
            "ui": {
                "resourceUri": ui_resource_uri
            }
        }
    }
    return json.dumps(payload, indent=2)

# FastMCP HTTP ASGI App (Stateless HTTP mode)
mcp_http = mcp_app.http_app(path="/mcp", stateless_http=True)
