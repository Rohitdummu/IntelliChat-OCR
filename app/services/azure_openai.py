
import logging

from langchain_openai import ChatOpenAI

from app.core.config import settings


logger = logging.getLogger(__name__)


class AzureOpenAIService:

    def __init__(self):

        logger.info("Initializing Azure OpenAI service...")

        if not settings.AZURE_OPENAI_ENDPOINT:
            raise ValueError("Azure OpenAI endpoint is missing")

        if not settings.AZURE_OPENAI_API_KEY:
            raise ValueError("Azure OpenAI API key is missing")

        if not settings.AZURE_OPENAI_CHAT_DEPLOYMENT:
            raise ValueError("Azure OpenAI deployment is missing")

        self.llm = ChatOpenAI(
            model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            base_url=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY
        )

        logger.info(
            "Azure OpenAI client initialized successfully. Deployment: %s",
            settings.AZURE_OPENAI_CHAT_DEPLOYMENT
        )

    def generate_response(self, prompt: str) -> str:

        logger.info("Sending request to Azure OpenAI...")

        try:
            response = self.llm.invoke(prompt)

            logger.info(
                "Azure OpenAI response received successfully."
            )

            return response.content

        except Exception:
            logger.exception(
                "Azure OpenAI request failed."
            )
            raise

    def check_connection(self) -> bool:

        logger.info(
            "Checking Azure OpenAI connectivity..."
        )

        try:
            response = self.llm.invoke(
                "Reply with exactly: AZURE_OPENAI_CONNECTED"
            )

            if "AZURE_OPENAI_CONNECTED" in response.content:
                logger.info(
                    "Azure OpenAI connection verified successfully."
                )
                return True

            logger.warning(
                "Azure OpenAI responded, but the verification message differed."
            )
            return False

        except Exception:
            logger.exception(
                "Azure OpenAI connectivity check failed."
            )
            return False
