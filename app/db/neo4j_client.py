import logging
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from app.config import settings

logger = logging.getLogger(__name__)

class Neo4jConnection:
    _driver: Optional[Driver] = None
    _tried_connect: bool = False

    @classmethod
    def get_driver(cls) -> Optional[Driver]:
        if cls._driver is None and not cls._tried_connect:
            cls._tried_connect = True
            try:
                cls._driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )
                cls._driver.verify_connectivity()
                logger.info("Connected to Neo4j successfully at %s", settings.NEO4J_URI)
            except Exception as e:
                logger.warning("Could not connect to Neo4j (%s). Ensure Neo4j service is running.", e)
                cls._driver = None
        return cls._driver

    @classmethod
    def reset_driver(cls):
        if cls._driver is not None:
            try:
                cls._driver.close()
            except Exception:
                pass
        cls._driver = None
        cls._tried_connect = False

    @classmethod
    def close(cls):
        cls.reset_driver()

def run_cypher(query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    driver = Neo4jConnection.get_driver()
    if driver is None:
        return []
    
    try:
        with driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    except (ServiceUnavailable, SessionExpired) as e:
        logger.warning("Neo4j connection dropped (%s). Resetting connection driver.", e)
        Neo4jConnection.reset_driver()
        return []
    except Exception as e:
        logger.warning("Neo4j execution exception (%s).", e)
        return []
