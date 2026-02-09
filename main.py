#!/usr/bin/env python3
"""
Main entry point for the Tableau Dashboard Generator application.

This script initializes the application and launches the Streamlit web interface.

Usage:
    python main.py                    # Run with default settings
    streamlit run main.py            # Run via Streamlit CLI
    
Environment Variables:
    AZURE_OPENAI_ENDPOINT             # Azure OpenAI endpoint URL
    AZURE_OPENAI_API_KEY              # Azure OpenAI API key
    AZURE_OPENAI_DEPLOYMENT_NAME      # Azure OpenAI deployment name
    LOG_LEVEL                         # Logging level (DEBUG, INFO, WARNING, ERROR)
    
Configuration:
    The application uses config.yaml for default settings and .env for secrets.
    Copy .env.template to .env and fill in your Azure OpenAI credentials.
"""

import sys
import os
from pathlib import Path


# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main application entry point"""
    try:
        # Import after adding src to path
        from src.utils.logger import init_default_logging, get_logger
        from src.utils.config import get_config
        from src.ui.streamlit_app import main as run_streamlit_app
        
        # Initialize logging first
        init_default_logging()
        logger = get_logger(__name__)
        
        logger.info("=" * 60)
        logger.info("Starting Tableau Dashboard Generator")
        logger.info("=" * 60)
        
        # Load and validate configuration
        try:
            config = get_config()
            logger.info(f"Application: {config.application.name} v{config.application.version}")
            logger.info(f"Debug mode: {config.application.debug}")
            logger.info(f"Log level: {config.application.log_level}")
            
            # Check LLM provider configuration
            provider = config.application.llm_provider if hasattr(config.application, 'llm_provider') else 'azure'
            logger.info(f"LLM Provider: {provider}")
            
            if provider.lower() in ('azure', 'azureopenai', 'azure_openai'):
                if not config.azure_openai.api_key:
                    logger.warning("Azure OpenAI API key not configured - some features may not work")
                else:
                    logger.info("Azure OpenAI configuration loaded")
            elif provider.lower() in ('gemini', 'google'):
                if config.llm.api_key:
                    logger.info("Google Gemini configuration loaded")
                else:
                    logger.warning("Google Gemini API key not configured - some features may not work")
            else:
                logger.info(f"Using {provider} as LLM provider")
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            logger.error("Please check your .env file and config.yaml")
            sys.exit(1)
        
        # Launch Streamlit application
        logger.info("Launching Streamlit web interface...")
        run_streamlit_app()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'streamlit',
        'openai', 
        'langchain',
        'langgraph',
        'pandas',
        'pydantic',
        'pyyaml',
        'python-dotenv',
        'loguru',
        'lxml'
    ]
    
    missing_packages = []
    # Some pip package names differ from their import names (e.g. PyYAML -> yaml,
    # python-dotenv -> dotenv). Provide a mapping to check the correct module.
    import_name_map = {
        'pyyaml': 'yaml',
        'python-dotenv': 'dotenv',
        'python_dotenv': 'dotenv',
        'langchain-openai': 'langchain_openai',
    }

    for package in required_packages:
        import_name = import_name_map.get(package, package.replace('-', '_'))
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages:", file=sys.stderr)
        for package in missing_packages:
            print(f"  - {package}", file=sys.stderr)
        print("\nInstall missing packages with:", file=sys.stderr)
        print(f"  pip install {' '.join(missing_packages)}", file=sys.stderr)
        sys.exit(1)

def setup_environment():
    """Set up the application environment"""
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required", file=sys.stderr)
        sys.exit(1)
    
    # Check dependencies
    check_dependencies()
    
    # Create required directories
    directories = [
        "data/uploads",
        "data/outputs", 
        "data/temp",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Check for .env file
    env_file = Path(".env")
    env_template = Path(".env.template")
    
    if not env_file.exists() and env_template.exists():
        print("Warning: .env file not found.", file=sys.stderr)
        print("Please copy .env.template to .env and configure your settings.", file=sys.stderr)
        print("The application may not work correctly without proper configuration.", file=sys.stderr)

if __name__ == "__main__":
    # Setup environment before running
    setup_environment()
    
    # Run the main application
    main()