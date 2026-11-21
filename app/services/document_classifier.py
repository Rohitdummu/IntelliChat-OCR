
import logging

from app.core.config import settings
from app.services.doc_intelligence import ContentUnderstandingClient

logger = logging.getLogger(__name__)


class DocumentClassifier:

    ALLOWED_CATEGORIES = {
        "insurance_claim_form",
        "discharge_summary",
        "hospital_bill",
        "laboratory_report",
        "other"
    }

    def __init__(self):

        self.client = ContentUnderstandingClient(
            analyzer_id=settings.CONTENTUNDERSTANDING_CLASSIFIER_ID
        )

    async def classify_document(self, sas_url: str) -> dict:
        """
        Classify an insurance document using Azure Content Understanding.
        """

        logger.info("Starting document classification")

        # 1. Call Azure classifier
        result = await self.client.analyze_document(
            sas_url=sas_url
        )

        # 2. Extract contents
        analysis_result = result.get("result", {})
        contents = analysis_result.get("contents", [])

        detected_categories = []

        # 3. Read category from document segments
        for content in contents:

            for segment in content.get("segments", []):

                category = segment.get("category")

                if category:
                    normalized_category = category.strip().lower()
                    detected_categories.append(normalized_category)

        if not detected_categories:
            logger.warning("No category found in classifier response")
            return {
                "document_type": "other",
                "raw_result": result
            }

        # 4. Identify unique categories
        unique_categories = set(detected_categories)

        if len(unique_categories) > 1:

            logger.warning(
                "Multiple document categories detected: %s",
                unique_categories
            )

            return {
                "document_type": "multiple_documents",
                "categories": list(unique_categories),
                "raw_result": result
            }

        document_type = detected_categories[0]

        # 5. Validate category
        if document_type not in self.ALLOWED_CATEGORIES:
            logger.warning(
                "Unknown category detected: %s",
                document_type
            )
            document_type = "other"

        logger.info(
            "Document classification completed: %s",
            document_type
        )

        return {
            "document_type": document_type,
            "raw_result": result
        }
