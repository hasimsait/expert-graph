from typing import List, Optional
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "ExpertGraph"
    BASE_URL: str = "http://localhost:8000"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "expertgraph123"
    
    # LLM Settings (supports openai, gemini, ollama, local_openai)
    LLM_PROVIDER: str = "local-openai"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "llama3.1"
    LLM_BASE_URL: str = "http://localhost:8080/v1"
    OLLAMA_HOST: str = "http://localhost:8080"
    MAX_TOKENS: int = 500

    # Stop tokens — comma-separated env var, used only for local LLM providers
    STOP_TOKENS_RAW: str = Field(default="<eos>,<|im_end|>,<|endoftext|>", alias="STOP_TOKENS")

    # Entity Resolution Settings
    ONTOLOGY_PATH: str = ""

    # Prompt Management Settings
    PROMPTS_DIR: str = "prompts"
    EXTRACTION_PROMPT: Optional[str] = None
    CRITIC_PROMPT: Optional[str] = None

    model_config = ConfigDict(env_file=".env")

    def get_stop_tokens(self) -> List[str]:
        """Return stop tokens appropriate for the current provider.
        
        Cloud providers (openai, gemini) get an empty list since these
        tokens are specific to local/open-source models and may cause
        errors or truncated output on cloud APIs.
        """
        provider = self.LLM_PROVIDER.lower().replace("-", "_")
        if provider in ("openai", "gemini"):
            return []
        raw = self.STOP_TOKENS_RAW.strip()
        if not raw:
            return []
        return [t.strip() for t in raw.split(",") if t.strip()]

settings = Settings()

