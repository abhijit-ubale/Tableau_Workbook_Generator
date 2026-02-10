"""
Configuration management for the Tableau Dashboard Generator.
Handles loading and validation of application configuration from various sources.
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

class LLMConfig(BaseModel):
    """Generic LLM configuration to support multiple providers."""
    provider: str = "gemini"
    model_name: str = "gemini-2.5-flash"
    api_key: str = ""
    endpoint: str = ""
    deployment_name: str = ""
    api_version: str = "2024-02-15-preview"
    extra_kwargs: Dict[str, Any] = Field(default_factory=dict)

class AzureOpenAIConfig(BaseModel):
    """Azure OpenAI configuration"""
    endpoint: str
    api_key: str
    api_version: str
    deployment_name: str
    model_name: str
    temperature: float = 0.3
    max_tokens: int = 4000
    top_p: float = 0.9
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if v < 0 or v > 2:
            raise ValueError('temperature must be between 0 and 2')
        return v
    
    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v):
        if v < 1:
            raise ValueError('max_tokens must be positive')
        return v

class ApplicationConfig(BaseModel):
    """Application-level configuration"""
    name: str = "Tableau Dashboard Generator"
    version: str = "1.0.0"
    description: str = "AI-powered automatic Tableau dashboard generation"
    debug: bool = False
    log_level: str = "INFO"
    llm_provider: str = "azure"

class FileStorageConfig(BaseModel):
    """File storage configuration"""
    upload_folder: str = "./data/uploads"
    output_folder: str = "./data/outputs"
    temp_folder: str = "./data/temp"
    max_file_size_mb: int = 100

class DashboardGenerationConfig(BaseModel):
    """Dashboard generation configuration"""
    max_worksheets_per_workbook: int = 10
    max_dashboards_per_workbook: int = 5
    default_width: int = 1200
    default_height: int = 800
    visualization_types: Dict[str, List[str]] = Field(default_factory=dict)
    color_schemes: Dict[str, Any] = Field(default_factory=dict)

class DataProcessingConfig(BaseModel):
    """Data processing configuration"""
    max_file_size_mb: int = 100
    supported_formats: List[str] = Field(default_factory=lambda: ["csv", "xlsx", "json", "parquet"])
    auto_detect_types: bool = True
    sample_rows_for_analysis: int = 1000
    null_threshold: float = 0.3

class MetaPromptingConfig(BaseModel):
    """Meta-prompting configuration"""
    system_prompts: Dict[str, str] = Field(default_factory=dict)

class StreamlitConfig(BaseModel):
    """Streamlit configuration"""
    server_port: int = 8501
    server_address: str = "localhost"
    page_config: Dict[str, Any] = Field(default_factory=dict)

class Config:
    """
    Main configuration class that loads and manages all application settings.
    """
    
    def __init__(self, config_file: Optional[str] = None, env_file: Optional[str] = None):
        """
        Initialize configuration from file and environment variables.
        
        Args:
            config_file: Path to YAML configuration file
            env_file: Path to .env file
        """
        # Load environment variables
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()  # Load from default .env file if exists
        
        # Load configuration file
        self.config_data = self._load_config_file(config_file or "config.yaml")
        
        # Initialize configuration sections
        self.azure_openai = self._init_azure_openai_config()
        self.application = self._init_application_config()
        # Generic LLM configuration (may detect GEMINI_API_KEY)
        self.llm = self._init_llm_config()
        # Mirror chosen provider into application.llm_provider for compatibility
        try:
            self.application.llm_provider = self.llm.provider
        except Exception:
            pass

        self.file_storage = self._init_file_storage_config()
        self.dashboard_generation = self._init_dashboard_generation_config()
        self.data_processing = self._init_data_processing_config()
        self.meta_prompting = self._init_meta_prompting_config()
        self.streamlit = self._init_streamlit_config()
        
        # Validate configuration
        self._validate_config()
    
    def _load_config_file(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_path = Path(config_file)
        
        if not config_path.exists():
            # Create default config if it doesn't exist
            return self._create_default_config()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load config file {config_file}: {e}")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        return {
            "application": {
                "name": "Tableau Dashboard Generator",
                "version": "1.0.0",
                "description": "AI-powered automatic Tableau dashboard generation"
            },
            "azure_openai": {
                "api_version": "2024-02-15-preview",
                "max_tokens": 4000,
                "temperature": 0.3,
                "top_p": 0.9
            },
            "dashboard_generation": {
                "max_worksheets_per_workbook": 10,
                "max_dashboards_per_workbook": 5,
                "default_dimensions": {"width": 1200, "height": 800},
                "visualization_types": {
                    "numeric": ["bar", "line", "area", "scatter", "histogram"],
                    "categorical": ["bar", "pie", "treemap", "packed_bubbles"],
                    "geographic": ["map", "filled_map"],
                    "temporal": ["line", "area", "gantt"]
                },
                "color_schemes": {
                    "default": "tableau10",
                    "categorical": ["tableau10", "tableau20", "category10"],
                    "sequential": ["blues", "oranges", "greens"],
                    "diverging": ["red_blue", "orange_blue", "green_orange"]
                }
            },
            "data_processing": {
                "max_file_size_mb": 100,
                "supported_formats": ["csv", "xlsx", "json", "parquet"],
                "auto_detect_types": True,
                "sample_rows_for_analysis": 1000,
                "null_threshold": 0.3
            },
            "meta_prompting": {
                "system_prompts": {
                    "data_analyzer": "You are an expert data analyst specializing in business intelligence and Tableau dashboard design.",
                    "dashboard_designer": "You are a professional Tableau dashboard designer with expertise in creating compelling dashboards.",
                    "worksheet_creator": "You are a Tableau worksheet specialist."
                }
            },
            "streamlit": {
                "page_config": {
                    "page_title": "Tableau Dashboard Generator",
                    "page_icon": "📊",
                    "layout": "wide",
                    "initial_sidebar_state": "expanded"
                }
            }
        }
    
    def _init_azure_openai_config(self) -> AzureOpenAIConfig:
        """Initialize Azure OpenAI configuration"""
        config = self.config_data.get("azure_openai", {})
        
        return AzureOpenAIConfig(
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", config.get("api_version", "2024-02-15-preview")),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", ""),
            model_name=os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4-turbo"),
            temperature=float(os.getenv("AZURE_OPENAI_TEMPERATURE", config.get("temperature", 0.3))),
            max_tokens=int(os.getenv("AZURE_OPENAI_MAX_TOKENS", config.get("max_tokens", 4000))),
            top_p=float(os.getenv("AZURE_OPENAI_TOP_P", config.get("top_p", 0.9)))
        )
    
    def _init_application_config(self) -> ApplicationConfig:
        """Initialize application configuration"""
        config = self.config_data.get("application", {})
        
        return ApplicationConfig(
            name=os.getenv("APP_NAME", config.get("name", "Tableau Dashboard Generator")),
            version=os.getenv("APP_VERSION", config.get("version", "1.0.0")),
            description=config.get("description", "AI-powered automatic Tableau dashboard generation"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            llm_provider=os.getenv("LLM_PROVIDER", config.get("llm_provider", "azure"))
        )
    
    def _init_file_storage_config(self) -> FileStorageConfig:
        """Initialize file storage configuration"""
        return FileStorageConfig(
            upload_folder=os.getenv("UPLOAD_FOLDER", "./data/uploads"),
            output_folder=os.getenv("OUTPUT_FOLDER", "./data/outputs"),
            temp_folder=os.getenv("TEMP_FOLDER", "./data/temp"),
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "100"))
        )
    
    def _init_dashboard_generation_config(self) -> DashboardGenerationConfig:
        """Initialize dashboard generation configuration"""
        config = self.config_data.get("dashboard_generation", {})
        
        return DashboardGenerationConfig(
            max_worksheets_per_workbook=config.get("max_worksheets_per_workbook", 10),
            max_dashboards_per_workbook=config.get("max_dashboards_per_workbook", 5),
            default_width=config.get("default_dimensions", {}).get("width", 1200),
            default_height=config.get("default_dimensions", {}).get("height", 800),
            visualization_types=config.get("visualization_types", {}),
            color_schemes=config.get("color_schemes", {})
        )
    
    def _init_data_processing_config(self) -> DataProcessingConfig:
        """Initialize data processing configuration"""
        config = self.config_data.get("data_processing", {})
        
        return DataProcessingConfig(
            max_file_size_mb=config.get("max_file_size_mb", 100),
            supported_formats=config.get("supported_formats", ["csv", "xlsx", "json", "parquet"]),
            auto_detect_types=config.get("auto_detect_types", True),
            sample_rows_for_analysis=config.get("sample_rows_for_analysis", 1000),
            null_threshold=config.get("null_threshold", 0.3)
        )
    
    def _init_meta_prompting_config(self) -> MetaPromptingConfig:
        """Initialize meta-prompting configuration"""
        config = self.config_data.get("meta_prompting", {})
        
        return MetaPromptingConfig(
            system_prompts=config.get("system_prompts", {})
        )

    def _init_llm_config(self) -> LLMConfig:
        """Initialize a generic LLM configuration from env/config.yaml."""
        config = self.config_data.get("llm", {})

        # If the user placed a GEMINI_API_KEY and didn't explicitly set LLM_PROVIDER,
        # prefer Gemini (Google Gemini) as the provider.
        env_provider = os.getenv("LLM_PROVIDER")
        # Accept common Gemeni env var names (user may have used `gem_key`)
        gemini_env = os.getenv("GEMINI_API_KEY") or os.getenv("GEM_KEY") or os.getenv("gem_key")

        provider = (
            env_provider
            or config.get("provider")
            or ("gemini" if gemini_env else "azure")
        )

        model_name = os.getenv(
            "LLM_MODEL_NAME",
            config.get("model_name", os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4-turbo")),
        )

        # Prefer specific env vars if present
        api_key = (
            os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("AZURE_OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or gemini_env
            or os.getenv("GROK_API_KEY")
            or config.get("api_key", "")
        )

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", config.get("endpoint", ""))
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", config.get("deployment_name", ""))
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", config.get("api_version", "2024-02-15-preview"))
        extra_kwargs = config.get("extra_kwargs", {})

        return LLMConfig(
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            endpoint=endpoint,
            deployment_name=deployment_name,
            api_version=api_version,
            extra_kwargs=extra_kwargs,
        )
    
    def _init_streamlit_config(self) -> StreamlitConfig:
        """Initialize Streamlit configuration"""
        config = self.config_data.get("streamlit", {})
        
        return StreamlitConfig(
            server_port=int(os.getenv("STREAMLIT_SERVER_PORT", "8501")),
            server_address=os.getenv("STREAMLIT_SERVER_ADDRESS", "localhost"),
            page_config=config.get("page_config", {})
        )
    
    def _validate_config(self):
        """Validate configuration settings"""
        errors = []
        
        # Validate Azure OpenAI configuration only when Azure provider selected
        if self.application.llm_provider and self.application.llm_provider.lower() in ("azure", "azureopenai", "azure_openai"):
            if not self.azure_openai.endpoint:
                errors.append("Azure OpenAI endpoint is required for Azure provider")
            if not self.azure_openai.api_key:
                errors.append("Azure OpenAI API key is required for Azure provider")
            if not self.azure_openai.deployment_name:
                errors.append("Azure OpenAI deployment name is required for Azure provider")
        
        # Validate file paths
        for folder in [self.file_storage.upload_folder, self.file_storage.output_folder, self.file_storage.temp_folder]:
            try:
                Path(folder).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create directory {folder}: {e}")
        
        # Validate numeric ranges
        # Validate token/temperature ranges if available
        try:
            temp = float(self.azure_openai.temperature)
            if temp < 0 or temp > 2:
                errors.append("Azure OpenAI temperature must be between 0 and 2")
        except Exception:
            pass

        try:
            if int(self.azure_openai.max_tokens) < 1:
                errors.append("Azure OpenAI max_tokens must be positive")
        except Exception:
            pass
        
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "azure_openai": self.azure_openai.model_dump(),
            "application": self.application.model_dump(),
            "llm": {
                **self.llm.model_dump(),
                "api_key": bool(self.llm.api_key)  # Don't expose actual key
            },
            "file_storage": self.file_storage.model_dump(),
            "dashboard_generation": self.dashboard_generation.model_dump(),
            "data_processing": self.data_processing.model_dump(),
            "meta_prompting": self.meta_prompting.model_dump(),
            "streamlit": self.streamlit.model_dump()
        }

# Global configuration instance
_config_instance: Optional[Config] = None

def get_config(config_file: Optional[str] = None, env_file: Optional[str] = None) -> Config:
    """Get the global configuration instance"""
    global _config_instance
    
    if _config_instance is None:
        _config_instance = Config(config_file, env_file)
    
    return _config_instance

def reset_config():
    """Reset the global configuration instance"""
    global _config_instance
    _config_instance = None