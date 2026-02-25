"""Cyperf Applications and Application Types integration service.

Fetches application and application type data from Cyperf Controller,
saves to JSON files, and ingests into the database.
"""

import json
import logging
import os
from dataclasses import dataclass

try:
    import cyperf
except ImportError as _import_err:
    raise ImportError(
        "cyperf-api-wrapper not installed; run: pip install cyperf-api-wrapper"
    ) from _import_err

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.cyperf_application import CyperfApplication
from db.cyperf_application_type import CyperfApplicationType

logger = logging.getLogger(__name__)

BATCH_SIZE = 500
APPLICATIONS_FILE = "./data/cyperf_applications.json"
APPLICATION_TYPES_FILE = "./data/cyperf_application_types.json"


@dataclass
class ApplicationRecord:
    """Single application record."""

    app_id: str
    app_name: str
    app_description: str | None


@dataclass
class ApplicationTypeRecord:
    """Single application type record."""

    app_id: str
    app_name: str
    app_description: str | None


class CyperfApplicationsService:
    """Service for fetching Cyperf applications and application types."""

    def __init__(self, controller_ip: str, username: str, password: str) -> None:
        """Initialize with Cyperf credentials.

        Args:
            controller_ip: Cyperf Controller IP/hostname
            username: Cyperf Controller username
            password: Cyperf Controller password
        """
        self.controller_ip = controller_ip
        self._config = cyperf.Configuration(
            host=f"https://{controller_ip}",
            username=username,
            password=password,
        )
        self._config.verify_ssl = False

        logger.info(f"Initialized CyperfApplicationsService for {controller_ip}")

    async def fetch_application_types(self) -> list[ApplicationTypeRecord]:
        """Fetch all application types from Cyperf.

        Uses ApplicationResourcesApi.get_resources_application_types() with batching.

        Returns:
            List of ApplicationTypeRecord objects
        """
        application_types = []
        skip = 0

        try:
            with cyperf.ApiClient(self._config) as api_client:
                api_instance = cyperf.ApplicationResourcesApi(api_client)

                while True:
                    response = api_instance.get_resources_application_types(
                        take=BATCH_SIZE, skip=skip
                    )
                    data = response.data or []

                    if len(data) == 0:
                        break

                    for app_type in data:
                        record = ApplicationTypeRecord(
                            app_id=app_type.id,
                            app_name=app_type.name,
                            app_description=app_type.description or None,
                        )
                        application_types.append(record)
                        logger.debug(f"Fetched app type: {app_type.id} | {app_type.name}")

                    skip += BATCH_SIZE

            logger.info(f"Fetched {len(application_types)} application types")
            return application_types

        except Exception as e:
            logger.error(f"Error fetching application types: {e}")
            raise

    async def fetch_applications(self) -> list[ApplicationRecord]:
        """Fetch all applications from Cyperf.

        Uses ApplicationResourcesApi.get_resources_apps() with batching.

        Returns:
            List of ApplicationRecord objects
        """
        applications = []
        skip = 0

        try:
            with cyperf.ApiClient(self._config) as api_client:
                api_instance = cyperf.ApplicationResourcesApi(api_client)

                while True:
                    response = api_instance.get_resources_apps(take=BATCH_SIZE, skip=skip)
                    data = response.data or []

                    if len(data) == 0:
                        break

                    for app in data:
                        record = ApplicationRecord(
                            app_id=app.id,
                            app_name=app.name,
                            app_description=app.description or None,
                        )
                        applications.append(record)
                        logger.debug(f"Fetched application: {app.id} | {app.name}")

                    skip += BATCH_SIZE

            logger.info(f"Fetched {len(applications)} applications")
            return applications

        except Exception as e:
            logger.error(f"Error fetching applications: {e}")
            raise

    @staticmethod
    def _save_to_json(filename: str, data: list) -> None:
        """Save data to JSON file.

        Args:
            filename: Path to JSON file
            data: List of records to save
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
            with open(filename, "w") as f:
                # Convert dataclass objects to dicts
                data_dicts = [
                    {
                        "app_id": record.app_id,
                        "app_name": record.app_name,
                        "app_description": record.app_description,
                    }
                    for record in data
                ]
                json.dump(data_dicts, f, indent=2)
            logger.info(f"Saved {len(data)} records to {filename}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
            raise

    @staticmethod
    async def ingest_application_types(
        session: AsyncSession, records: list[ApplicationTypeRecord]
    ) -> None:
        """Ingest application type records into database.

        Performs full-replace: delete all existing records, insert fresh ones.

        Args:
            session: AsyncSession for database operations
            records: List of ApplicationTypeRecord objects
        """
        try:
            async with session.begin():
                # Full-replace: delete all existing
                await session.execute(delete(CyperfApplicationType))

                # Insert new records
                for record in records:
                    session.add(
                        CyperfApplicationType(
                            id=record.app_id,
                            name=record.app_name,
                            description=record.app_description,
                        )
                    )

            logger.info(f"Ingested {len(records)} application types into database")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error ingesting application types: {e}")
            raise

    @staticmethod
    async def ingest_applications(session: AsyncSession, records: list[ApplicationRecord]) -> None:
        """Ingest application records into database.

        Performs full-replace: delete all existing records, insert fresh ones.

        Args:
            session: AsyncSession for database operations
            records: List of ApplicationRecord objects
        """
        try:
            async with session.begin():
                # Full-replace: delete all existing
                await session.execute(delete(CyperfApplication))

                # Insert new records
                for record in records:
                    session.add(
                        CyperfApplication(
                            id=record.app_id,
                            name=record.app_name,
                            description=record.app_description,
                        )
                    )

            logger.info(f"Ingested {len(records)} applications into database")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error ingesting applications: {e}")
            raise
