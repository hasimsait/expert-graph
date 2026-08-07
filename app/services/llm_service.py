import logging
from typing import Any, Dict, Optional
import instructor
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    """Service for managing LLM client initialization and configuration."""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower().replace("-", "_")
        self.base_url = self._get_base_url()
        self.api_key = settings.OPENAI_API_KEY if settings.OPENAI_API_KEY else "local"
        
        # Use instructor's JSON mode for non-OpenAI models, otherwise TOOLS mode
        self.mode = instructor.Mode.MD_JSON if self.provider != "openai" else instructor.Mode.TOOLS

        # Cache the client to prevent connection pool leaks
        self._client = instructor.from_openai(
            AsyncOpenAI(base_url=self.base_url, api_key=self.api_key), 
            mode=self.mode
        )        
    def _get_base_url(self) -> Optional[str]:
        base_url = settings.LLM_BASE_URL if self.provider != "openai" else None
        if base_url:
            if not (base_url.startswith("http://") or base_url.startswith("https://")):
                base_url = f"http://{base_url}"
            base_url = base_url.rstrip("/")
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
        return base_url

    def get_instructor_client(self) -> instructor.AsyncInstructor:
        """Get the cached AsyncInstructor client."""
        return self._client
        
    def get_llm_kwargs(self, response_model: type, messages: list[Dict[str, str]]) -> Dict[str, Any]:
        """Get common kwargs for the LLM chat completion call."""
        kwargs = {
            "model": settings.LLM_MODEL,
            "response_model": response_model,
            "max_tokens": settings.MAX_TOKENS,
            "messages": messages
        }
        
        # Only include stop tokens for local providers
        stop_tokens = settings.get_stop_tokens()
        if stop_tokens:
            kwargs["stop"] = stop_tokens
            
        return kwargs

_llm_service_instance: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    """Get the global LLMService singleton instance."""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance
