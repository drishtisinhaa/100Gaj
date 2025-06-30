from llama_index.core import SimpleDirectoryReader
from .settings import settings

def get_documents():
    """Loads all documents from the configured data directory."""
    return SimpleDirectoryReader(settings.data_dir).load_data()