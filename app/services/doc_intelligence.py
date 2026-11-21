
import asyncio
import httpx
from app.core.config import settings


# API_VERSION = "2025-11-01"


# async def analyze_document(sas_url: str):

#     endpoint = settings.CONTENTUNDERSTANDING_ENDPOINT.rstrip("/")
#     analyzer_id = settings.CONTENTUNDERSTANDING_ANALYZER_ID

#     headers = {
#         "Ocp-Apim-Subscription-Key": settings.CONTENTUNDERSTANDING_KEY,
#         "Content-Type": "application/json"
#     }

#     analyze_url = (
#         f"{endpoint}/contentunderstanding/analyzers/"
#         f"{analyzer_id}:analyze?api-version={API_VERSION}"
#     )

#     async with httpx.AsyncClient(
#         timeout=httpx.Timeout(60.0, connect=15.0)
#     ) as client:

#         # 1. Submit document for analysis
#         response = await client.post(
#             analyze_url,
#             headers=headers,
#             json={
#                 "inputs": [
#                     {
#                         "url": sas_url
#                     }
#                 ]
#             }
#         )

#         response.raise_for_status()

#         # 2. Get operation URL
#         operation_url = response.headers.get("Operation-Location")

#         if not operation_url:
#             raise RuntimeError("Operation-Location header missing")

#         # 3. Poll for analysis result
#         for attempt in range(150):

#             await asyncio.sleep(2)

#             result_response = await client.get(
#                 operation_url,
#                 headers=headers
#             )

#             result_response.raise_for_status()

#             result_data = result_response.json()
#             status = result_data.get("status")

#             if status == "Succeeded":

#                 analysis_result = result_data.get("result", {})

#                 return {
#                     "status": "completed",
#                     "analyzer_id": analyzer_id,
#                     "contents": analysis_result.get("contents", []),
#                     "warnings": analysis_result.get("warnings", [])
#                 }

#             if status == "Failed":
#                 raise RuntimeError(
#                     f"Content Understanding failed: {result_data}"
#                 )

#         raise TimeoutError(
#             "Document analysis timed out"
#         )



import asyncio
import logging

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class ContentUnderstandingClient:

    def __init__(self, analyzer_id: str | None = None):

        self.endpoint = (
            settings.CONTENTUNDERSTANDING_ENDPOINT.rstrip("/")
        )

        self.api_key = settings.CONTENTUNDERSTANDING_KEY

        self.api_version = (
            settings.CONTENTUNDERSTANDING_API_VERSION
        )

        self.headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.analyzer_id = (
            analyzer_id or settings.CONTENTUNDERSTANDING_ANALYZER_ID
        )

    async def analyze_document(self, sas_url: str) -> dict:
        """
        Submit a document to Azure Content Understanding
        and return the completed raw analysis response.
        """

        analyze_url = (
            f"{self.endpoint}/contentunderstanding/analyzers/"
            f"{self.analyzer_id}:analyze"
            f"?api-version={self.api_version}"
        )

        logger.info("Submitting document to Content Understanding")

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=15.0)
        ) as client:

            try:
                # Step 1: Submit document
                response = await client.post(
                    analyze_url,
                    headers=self.headers,
                    json={
                        "inputs": [
                            {"url": sas_url}
                        ]
                    }
                )

                response.raise_for_status()

                # Step 2: Get operation URL
                operation_url = response.headers.get(
                    "Operation-Location"
                )

                if not operation_url:
                    raise RuntimeError(
                        "Operation-Location header missing"
                    )

                logger.info(
                    "Document analysis submitted successfully"
                )

                # Step 3: Poll for result
                return await self._poll_result(
                    client,
                    operation_url
                )

            except httpx.HTTPStatusError:
                logger.exception(
                    "Content Understanding API returned an error"
                )
                raise

            except Exception:
                logger.exception(
                    "Content Understanding analysis failed"
                )
                raise

    async def _poll_result(
        self,
        client: httpx.AsyncClient,
        operation_url: str
    ) -> dict:
        """
        Poll Azure until document analysis completes.
        """

        max_attempts = 60
        poll_interval = 2

        for attempt in range(1, max_attempts + 1):

            await asyncio.sleep(poll_interval)

            response = await client.get(
                operation_url,
                headers=self.headers
            )

            response.raise_for_status()

            result = response.json()
            operation_status = result.get("status")

            logger.info(
                "Content Understanding polling",
                extra={
                    "attempt": attempt,
                    "operation_status": operation_status
                }
            )

            if operation_status == "Succeeded":

                logger.info(
                    "Content Understanding analysis completed"
                )

                return result

            if operation_status == "Failed":

                raise RuntimeError(
                    f"Document analysis failed: "
                    f"{result.get('error', 'Unknown error')}"
                )

        raise TimeoutError(
            "Content Understanding analysis timed out"
        )

