from pathlib import Path
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class ModelParams(BaseModel):
    window_size: int = 100
    sample_size: int = 50000
    recommend_count: int = 5


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        protected_namespaces=("settings_", "model_"),
    )

    ssq_csv_path: Path = DATA_DIR / "ssq_history.csv"
    dlt_csv_path: Path = DATA_DIR / "dlt_history.csv"
    model_params: ModelParams = ModelParams()


settings = Settings()

