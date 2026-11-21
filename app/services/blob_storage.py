
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import (
    BlobSasPermissions,
    generate_blob_sas
)

from app.core.config import settings


async def upload_to_blob(
    file_content: bytes,
    document_id: str
):

    blob_name = f"documents/{document_id}/{uuid4()}.pdf"

    # 1. Create async Blob Service Client
    async with BlobServiceClient.from_connection_string(
        settings.AZURE_STORAGE_CONNECTION_STRING
    ) as blob_service_client:

        # 2. Get container client
        container_client = blob_service_client.get_container_client(
            settings.AZURE_STORAGE_CONTAINER
        )

        # 3. Create container if not exists
        try:
            await container_client.create_container()
        except Exception as e:
            # Container already exists
            if "ContainerAlreadyExists" not in str(e):
                raise

        # 4. Get blob client
        blob_client = container_client.get_blob_client(blob_name)

        # 5. Upload PDF asynchronously
        await blob_client.upload_blob(
            file_content,
            overwrite=False,
            content_settings=None
        )

        # 6. Generate SAS token
        # SAS generation is a local signing operation,
        # so it does not need await.
        sas_token = generate_blob_sas(
            account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
            container_name=settings.AZURE_STORAGE_CONTAINER,
            blob_name=blob_name,
            account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=30)
        )

        sas_url = f"{blob_client.url}?{sas_token}"

        return {
            "blob_name": blob_name,
            "blob_url": blob_client.url,
            "sas_url": sas_url
        }


def generate_read_sas_url(blob_name: str) -> str:

    container_name = settings.AZURE_STORAGE_CONTAINER

    sas_token = generate_blob_sas(
        account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
        container_name=container_name,
        blob_name=blob_name,
        account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=1)
    )

    blob_url = (
        f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}"
        f".blob.core.windows.net/"
        f"{container_name}/{blob_name}"
    )

    return f"{blob_url}?{sas_token}"
