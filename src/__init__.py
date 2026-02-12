"""
Farm Plot Agent - Core Modules Package

Modules:
    - database: SQLite database management
    - translation: English-Telugu translation service
    - weather: Weather API integration
    - satellite: Satellite NDVI monitoring
    - visualization: Graph and chart generation
    - local_llm: Local Ollama LLM integration (optional)
    - agent: LangGraph-based orchestration engine
    - whatsapp: Messaging interface
"""

__version__ = "1.1.0"
__author__ = "Farm Agent Team"
__description__ = "AI-powered crop monitoring system for Indian smallholder farmers"

from . import database
from . import translation
from . import weather
from . import satellite
from . import visualization
from . import local_llm
from . import agent
from . import whatsapp

__all__ = [
    'database',
    'translation',
    'weather',
    'satellite',
    'visualization',
    'local_llm',    'agent',
    'whatsapp'
]