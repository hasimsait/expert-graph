import json
import logging
from fastmcp import FastMCP
from app.config import settings
from app.module_c_mcp.retrieval import fetch_approved_facts

logger = logging.getLogger(__name__)

mcp_app = FastMCP("ExpertGraph-MCP-Server")

@mcp_app.tool()
async def retrieve_verified_facts(query: str = "ALL") -> str:
    """
    Retrieves human-verified ground truth facts from the ExpertGraph Neo4j database for a search query or concept domain.
    
    Arguments:
        query: Search query, topic, or concept to retrieve facts for (e.g. 'breast cancer', 'HER2', 'mutation', 'OWES_DEBT', or 'ALL').
    """
    facts = fetch_approved_facts(query=query)
    base_url = getattr(settings, "BASE_URL", "http://localhost:8000")
    ui_resource_uri = f"{base_url}/ui/facts-widget?concept={query}"
    
    payload = {
        "query": query,
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
