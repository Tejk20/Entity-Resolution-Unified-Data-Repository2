from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Unified Entity Resolution Platform"
    database_url: str = "sqlite:///./data/entity_store.db"
    upload_dir: str = "./data/uploads"
    sample_dir: str = "./data/samples"
    batch_size: int = 5000
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "deepseek-chat"
    cors_origins: str = "*"


settings = Settings()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = Path(settings.upload_dir)
if not UPLOAD_DIR.is_absolute():
    UPLOAD_DIR = BASE_DIR / settings.upload_dir
SAMPLE_DIR = Path(settings.sample_dir)
if not SAMPLE_DIR.is_absolute():
    SAMPLE_DIR = BASE_DIR / settings.sample_dir

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
