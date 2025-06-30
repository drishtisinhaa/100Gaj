import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from llama_index.core.settings import Settings
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.gemini import GeminiEmbedding

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(APP_ROOT)
DATA_DIR = os.path.join(APP_ROOT, "data")
CACHE_DIR = os.path.join(PROJECT_ROOT, "cache")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    google_api_key: str
    data_dir: str = DATA_DIR
    cache_dir: str = CACHE_DIR

def init_settings():
    app_settings = AppSettings()
    os.environ["GOOGLE_API_KEY"] = app_settings.google_api_key

    Settings.llm = Gemini(model_name="models/gemini-1.5-flash-latest")
    Settings.embed_model = GeminiEmbedding(model_name="models/embedding-001")
    Settings.chunk_size = 1024
    Settings.chunk_overlap = 20
    
    print("LlamaIndex global settings initialized for pure RAG.")
    return app_settings

settings = init_settings()