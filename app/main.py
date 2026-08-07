import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.db.schema import init_db_schema
from app.module_b_annotator.router import router as annotator_router
from app.module_c_mcp.ui_widget import router as ui_widget_router
from app.api.analytics import router as analytics_router
from app.module_c_mcp.mcp_server import mcp_http
from app.core.container import Container
from app.db.neo4j_client import Neo4jConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize container globally for DI wiring
container = Container()
container.wire(packages=["app"])

@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Initialise shared resources on startup; gracefully clean up on shutdown."""
    logger.info("Starting ExpertGraph server — initializing Dual Graph database schema...")
    try:
        await init_db_schema()
        fastapi_app.container = container
        
        # Warmup index
        search_service = container.search_service()
        edge_repo = container.edge_repo()
        
        await search_service.warmup_from_db(edge_repo)
    except Exception as e:
        logger.warning("Database initialization warning: %s", e)
    
    logger.info("Starting FastMCP HTTP app lifespan...")
    async with mcp_http.lifespan(fastapi_app):
        logger.info("ExpertGraph application ready for requests.")
        yield  # Server active here

    logger.info("Shutting down ExpertGraph server — closing Neo4j database driver connection...")
    try:
        await Neo4jConnection.close()
        logger.info("Neo4j driver connection closed cleanly.")
    except Exception as e:
        logger.error("Error closing Neo4j driver connection: %s", e)

app = FastAPI(title="ExpertGraph API & Stateless MCP-UI Server", version="1.0.0", lifespan=lifespan)

# Health check
@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "ExpertGraph",
        "mcp_endpoint": "/mcp"
    }

# Include Annotator API, Analytics API, and UI Widget routes
app.include_router(annotator_router)
app.include_router(analytics_router)
app.include_router(ui_widget_router)

# Mount static React Annotator Dashboard build & assets
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static_dashboard")
ASSETS_DIR = os.path.join(STATIC_DIR, "assets")

if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

if os.path.exists(STATIC_DIR):
    app.mount("/dashboard", StaticFiles(directory=STATIC_DIR, html=True), name="dashboard")

@app.get("/", response_class=HTMLResponse)
def root_dashboard():
    """Serve React Annotator Dashboard at root endpoint."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse(
        content="""
        <html>
            <body style='font-family: sans-serif; background: #0f172a; color: white; padding: 2rem;'>
                <h1>ExpertGraph Backend Server Running (Stateless MCP HTTP Mode)</h1>
                <p>Status: Healthy</p>
                <ul>
                    <li><a style='color: #818cf8;' href='/api/queue'>Pending Queue API (/api/queue)</a></li>
                    <li><a style='color: #818cf8;' href='/api/stats'>Stats API (/api/stats)</a></li>
                    <li><a style='color: #818cf8;' href='/ui/facts-widget?concept=OWES_DEBT'>MCP-UI Facts Widget (/ui/facts-widget)</a></li>
                    <li><a style='color: #818cf8;' href='/mcp'>Stateless MCP HTTP Endpoint (/mcp)</a></li>
                </ul>
            </body>
        </html>
        """
    )

# Mount FastMCP HTTP App (provides /mcp endpoint in stateless HTTP mode)
app.mount("/", mcp_http)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
