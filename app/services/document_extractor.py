
import logging

from app.core.config import settings
from app.services.doc_intelligence import ContentUnderstandingClient

logger = logging.getLogger(__name__)


class DocumentExtractionService:

    ANALYZER_MAPPING = {
        "insurance_claim_form": "CONTENTUNDERSTANDING_CLAIM_FORM_ID",
        "discharge_summary": "CONTENTUNDERSTANDING_DISCHARGE_SUMMARY_ID",
        "hospital_bill": "CONTENTUNDERSTANDING_HOSPITAL_BILL_ID",
        "laboratory_report": "CONTENTUNDERSTANDING_LAB_REPORT_ID",
    }

    async def extract_document(
        self,
        document_type: str,
        sas_url: str
    ) -> dict:

        document_type = document_type.strip().lower()

        # 1. Identify the correct analyzer setting
        setting_name = self.ANALYZER_MAPPING.get(document_type)

        if not setting_name:
            logger.warning(
                "Unsupported document type for extraction: %s",
                document_type
            )
            raise ValueError(
                f"No extraction analyzer configured for: {document_type}"
            )

        # 2. Get analyzer ID from application settings
        analyzer_id = getattr(settings, setting_name)

        # 3. Initialize Azure client with selected analyzer
        client = ContentUnderstandingClient(
            analyzer_id=analyzer_id
        )

        logger.info(
            "Starting extraction for document type: %s",
            document_type
        )

        # 4. Submit document to Azure Content Understanding
        result = await client.analyze_document(sas_url)

        logger.info(
            "Extraction completed for document type: %s",
            document_type
        )

        return result


if __name__ == "__main__":
    import asyncio

    async def main():
        service = DocumentExtractionService()
        test_sas_url = "https://genaidemorohit.blob.core.windows.net/ocr-pdfs/documents/fd992648-59dd-4a6e-b9ed-e426a4292e6c/3547aead-d29b-46f0-95b4-2af354b15073.pdf"
        document_type = "hospital_bill"
        result = await service.extract_document(document_type, test_sas_url)
        print(result)

    asyncio.run(main())
