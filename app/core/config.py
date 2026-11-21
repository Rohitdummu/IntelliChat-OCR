
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):

    # Application
    APP_ENV: str = "development"

    # Database
    DATABASE_URL: str

    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_STORAGE_ACCOUNT_NAME: str = "genaidemorohit"
    AZURE_STORAGE_ACCOUNT_KEY: str = ""
    AZURE_STORAGE_CONTAINER: str = "ocr-pdfs"

    # Azure Content Understanding
    CONTENTUNDERSTANDING_ENDPOINT: str
    CONTENTUNDERSTANDING_KEY: str
    CONTENTUNDERSTANDING_API_VERSION: str = "2025-11-01"

    CONTENTUNDERSTANDING_ANALYZER_ID: str = "Banking_Analyzer"
    CONTENTUNDERSTANDING_CLASSIFIER_ID: str = "Healthcare_Document_Analyzer"

    CONTENTUNDERSTANDING_CLAIM_FORM_ID: str = "Claim_Form_Extractor"
    CONTENTUNDERSTANDING_DISCHARGE_SUMMARY_ID: str = "Discharge_Summary_Extractor"
    CONTENTUNDERSTANDING_HOSPITAL_BILL_ID: str = "Hospital_Bill_Extractor"
    CONTENTUNDERSTANDING_LAB_REPORT_ID: str = "Lab_Report_Extractor"

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_API_VERSION: str = "2025-11-13"
    AZURE_OPENAI_CHAT_DEPLOYMENT: str = "gpt-5.1"

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
        extra="ignore",
        case_sensitive=False
    )


settings = Settings()
