import os
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "ExpertGraph"
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "expertgraph123")
    
    # LLM Settings (supports openai, gemini, ollama, local_openai)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "local-openai")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3.1")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:8080/v1")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:8080")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "500"))
    STOP_TOKENS: list = ["<eos>", "<|tool_response>", "<|im_end|>", "<|endoftext|>"]

    # Entity Resolution Settings
    ONTOLOGY_PATH: str = os.getenv("ONTOLOGY_PATH", "")

    model_config = ConfigDict(env_file=".env")

settings = Settings()
