
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "app.db"


class Settings(BaseSettings):

    DATABASE_URL: str

    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_STORAGE_ACCOUNT_NAME: str
    AZURE_STORAGE_ACCOUNT_KEY: str
    AZURE_STORAGE_CONTAINER: str = "documents"

    CONTENTUNDERSTANDING_ENDPOINT: str
    CONTENTUNDERSTANDING_KEY: str
    CONTENTUNDERSTANDING_ANALYZER_ID: str
    CONTENTUNDERSTANDING_API_VERSION: str = "2025-11-01"
    CONTENTUNDERSTANDING_CLASSIFIER_ID: str
    CONTENTUNDERSTANDING_CLASSIFIER_ID: str

    CONTENTUNDERSTANDING_CLAIM_FORM_ID: str
    CONTENTUNDERSTANDING_DISCHARGE_SUMMARY_ID: str
    CONTENTUNDERSTANDING_HOSPITAL_BILL_ID: str
    CONTENTUNDERSTANDING_LAB_REPORT_ID: str

    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_API_VERSION: str
    AZURE_OPENAI_CHAT_DEPLOYMENT: str
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value):
        if not isinstance(value, str):
            return value

        if value.startswith("sqlite:///./"):
            relative_path = value.replace("sqlite:///./", "", 1)
            db_path = (PROJECT_ROOT / relative_path).resolve()
            return f"sqlite:///{db_path.as_posix()}"

        if value.startswith("sqlite:///") and not value.startswith("sqlite:////"):
            return value

        return value

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
