"""LLM provider factory to create chat LLM instances based on configuration.

This module centralizes LLM selection so the codebase can remain LLM-agnostic.
Supported providers: 'azure' (Azure OpenAI) and 'openai' (OpenAI hosted API).
"""

from typing import Any
from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


def create_chat_llm(cfg: Config) -> Any:
    """Return a chat LLM instance based on the provided Config.

    This function tries provider-specific LangChain chat classes first, then
    falls back to using the `instructor` library's `from_provider` helper if
    available. All imports are optional and produce helpful errors when missing.
    """
    # Prefer the generic llm config provider when available
    provider = None
    if getattr(cfg, "llm", None) and getattr(cfg.llm, "provider", None):
        provider = cfg.llm.provider
    else:
        provider = getattr(cfg.application, "llm_provider", "azure")
    provider = provider.lower()
    model_name = getattr(cfg, "llm", None).model_name if getattr(cfg, "llm", None) else (cfg.azure_openai.model_name if hasattr(cfg, "azure_openai") else None)

    # Azure OpenAI via langchain-openai
    if provider in ("azure", "azureopenai", "azure_openai"):
        try:
            from langchain_openai import AzureChatOpenAI
            # Prefer generic llm config values when available
            azure_endpoint = cfg.llm.endpoint or cfg.azure_openai.endpoint
            api_key = cfg.llm.api_key or cfg.azure_openai.api_key
            api_version = cfg.llm.api_version or cfg.azure_openai.api_version
            deployment_name = cfg.llm.deployment_name or cfg.azure_openai.deployment_name
            model = cfg.llm.model_name or cfg.azure_openai.model_name

            return AzureChatOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                api_version=api_version,
                deployment_name=deployment_name,
                model_name=model,
                temperature=cfg.llm.extra_kwargs.get("temperature", cfg.azure_openai.temperature) if cfg.llm.extra_kwargs else cfg.azure_openai.temperature,
                max_tokens=cfg.llm.extra_kwargs.get("max_tokens", cfg.azure_openai.max_tokens) if cfg.llm.extra_kwargs else cfg.azure_openai.max_tokens,
                top_p=cfg.llm.extra_kwargs.get("top_p", cfg.azure_openai.top_p) if cfg.llm.extra_kwargs else cfg.azure_openai.top_p,
            )
        except Exception as e:
            logger.error(f"Failed to create AzureChatOpenAI: {e}")
            raise

    # OpenAI hosted API via LangChain ChatOpenAI
    if provider in ("openai",):
        try:
            from langchain.chat_models import ChatOpenAI

            temp = cfg.llm.extra_kwargs.get("temperature") if cfg.llm and cfg.llm.extra_kwargs else cfg.azure_openai.temperature
            return ChatOpenAI(
                model_name=model_name or cfg.azure_openai.model_name,
                temperature=temp,
                verbose=False,
            )
        except Exception as e:
            logger.error(f"Failed to create ChatOpenAI: {e}")
            raise

    # Anthropic (Claude) via LangChain ChatAnthropic or instructor fallback
    if provider in ("anthropic",):
        # Try LangChain's ChatAnthropic first
        try:
            from langchain.chat_models import ChatAnthropic

            return ChatAnthropic(model= model_name or cfg.azure_openai.model_name)
        except Exception:
            # Fall back to instructor.from_provider if available
            try:
                import instructor

                return instructor.from_provider(f"anthropic/{model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                raise

    # Google Gemini / PaLM
    if provider in ("gemini", "palm", "google", "vertex"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            gemini_kwargs = {"model": model_name or "gemini-2.5-flash"}
            if getattr(cfg, "llm", None) and cfg.llm.api_key:
                gemini_kwargs["google_api_key"] = cfg.llm.api_key
            if getattr(cfg, "llm", None) and cfg.llm.extra_kwargs:
                gemini_kwargs.update(cfg.llm.extra_kwargs)

            return ChatGoogleGenerativeAI(**gemini_kwargs)
        except Exception as e:
            logger.error(f"Failed to create ChatGoogleGenerativeAI: {e}")
            raise

    # Grok / xAI or other OpenAI-compatible providers
    if provider in ("grok", "xai",):
        try:
            # Attempt to use OpenAI-compatible ChatOpenAI if available
            from langchain.chat_models import ChatOpenAI

            return ChatOpenAI(model_name=model_name or cfg.azure_openai.model_name, temperature=cfg.azure_openai.temperature)
        except Exception:
            try:
                import instructor

                return instructor.from_provider(f"grok/{model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Grok client: {e}")
                raise

    # Generic fallback: try instructor.from_provider with provider/model
    try:
        import instructor

        return instructor.from_provider(f"{provider}/{model_name}")
    except Exception as e:
        logger.error(f"Unsupported or unavailable LLM provider '{provider}': {e}")
        raise ValueError(f"Unsupported LLM provider: {provider}. Install the provider SDK or use 'azure'/'openai'.")
