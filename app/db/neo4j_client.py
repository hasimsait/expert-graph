import logging
from typing import Any, Dict, List, Optional
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from app.config import settings

logger = logging.getLogger(__name__)

class Neo4jConnection:
    _driver: Optional[AsyncDriver] = None
    _tried_connect: bool = False

    @classmethod
    async def get_driver(cls) -> Optional[AsyncDriver]:
        if cls._driver is None and not cls._tried_connect:
            cls._tried_connect = True
            try:
                cls._driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )
                await cls._driver.verify_connectivity()
                logger.info("Connected to Neo4j AsyncDriver successfully at %s", settings.NEO4J_URI)
            except Exception as e:
                logger.warning("Could not connect to Neo4j AsyncDriver (%s). Ensure Neo4j service is running.", e)
                cls._driver = None
        return cls._driver

    @classmethod
    async def reset_driver(cls):
        if cls._driver is not None:
            try:
                await cls._driver.close()
            except Exception:
                pass
        cls._driver = None
        cls._tried_connect = False

    @classmethod
    async def close(cls):
        await cls.reset_driver()

async def run_cypher(query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    driver = await Neo4jConnection.get_driver()
    if driver is None:
        return []
    
    try:
        async with driver.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records
    except (ServiceUnavailable, SessionExpired) as e:
        logger.warning("Neo4j async connection dropped (%s). Resetting connection driver.", e)
        await Neo4jConnection.reset_driver()
        return []
    except Exception as e:
        logger.warning("Neo4j async execution exception (%s).", e)
        return []
