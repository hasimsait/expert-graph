import logging
from typing import Any, Dict, List, Optional
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from app.config import settings

logger = logging.getLogger(__name__)

class Neo4jConnection:
    _driver: Optional[AsyncDriver] = None

    @classmethod
    async def get_driver(cls) -> AsyncDriver:
        """Get or create the Neo4j async driver. Retries connection each time if not connected."""
        if cls._driver is None:
            try:
                cls._driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )
                await cls._driver.verify_connectivity()
                logger.info("Connected to Neo4j AsyncDriver successfully at %s", settings.NEO4J_URI)
            except Exception as e:
                cls._driver = None
                raise ConnectionError(
                    f"Could not connect to Neo4j at {settings.NEO4J_URI}: {e}. "
                    "Ensure Neo4j service is running."
                ) from e
        return cls._driver

    @classmethod
    async def reset_driver(cls):
        if cls._driver is not None:
            try:
                await cls._driver.close()
            except Exception:
                pass
        cls._driver = None

    @classmethod
    async def close(cls):
        await cls.reset_driver()

async def run_cypher(query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Execute a Cypher query. Retries once on transient connection failures. Raises on persistent errors."""
    driver = await Neo4jConnection.get_driver()

    try:
        async with driver.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records
    except (ServiceUnavailable, SessionExpired) as e:
        logger.warning("Neo4j connection dropped (%s). Resetting driver and retrying once...", e)
        await Neo4jConnection.reset_driver()
        # Retry once after reconnection
        try:
            driver = await Neo4jConnection.get_driver()
            async with driver.session() as session:
                result = await session.run(query, parameters or {})
                records = await result.data()
                return records
        except Exception as retry_err:
            logger.error("Neo4j retry also failed: %s", retry_err)
            raise
    except Exception as e:
        logger.error("Neo4j query execution failed: %s | Query: %.200s", e, query.strip())
        raise
