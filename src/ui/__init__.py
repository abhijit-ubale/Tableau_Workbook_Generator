"""
UI package for the Tableau Dashboard Generator.
Provides Streamlit-based web interface for dashboard generation.
"""

# Lazy import to avoid circular imports
def __getattr__(name):
    if name == "StreamlitApp":
        from .streamlit_app import StreamlitApp
        return StreamlitApp
    elif name == "main":
        from .streamlit_app import main
        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "StreamlitApp",
    "main"
]