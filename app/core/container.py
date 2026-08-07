"""
Dependency Injection Container using dependency-injector
"""

from dependency_injector import containers, providers
from app.db.repository.edge_repo import Neo4jEdgeRepository
from app.db.repository.concept_repo import Neo4jConceptRepository
from app.db.repository.document_repo import Neo4jDocumentRepository
from app.services.search_service import SearchService, TFIDFSearchService
from app.services.graph_service import GraphService
from app.services.annotation_service import AnnotationService
from app.services.entity_resolution import EntityResolver

class Container(containers.DeclarativeContainer):
    """
    IoC container of application dependencies.
    """
    
    # Enable wiring on the packages that use dependencies
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.main",
            "app.module_b_annotator.router",
            "app.api.analytics",
            "app.module_c_mcp.ui_widget",
            "app.module_c_mcp.retrieval"
        ]
    )

    # Repositories
    edge_repo = providers.Singleton(Neo4jEdgeRepository)
    concept_repo = providers.Singleton(Neo4jConceptRepository)
    document_repo = providers.Singleton(Neo4jDocumentRepository)

    # Entity Resolver
    entity_resolver = providers.Singleton(EntityResolver)

    # Services
    search_service = providers.Singleton(
        TFIDFSearchService,
        edge_repo=edge_repo
    )
    
    graph_service = providers.Singleton(
        GraphService,
        concept_repo=concept_repo,
        document_repo=document_repo
    )
    
    annotation_service = providers.Singleton(
        AnnotationService,
        edge_repo=edge_repo,
        search_service=search_service,
        entity_resolver=entity_resolver,
        concept_repo=concept_repo
    )
