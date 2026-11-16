# Changes: database naming and bounded connection timeouts.
from datetime import UTC, datetime
from typing import Any

import certifi
from pymongo import MongoClient


class ReportStore:
    def __init__(self, uri: str):
        # Use certifi for SSL certificate verification with updated options
        self.client = MongoClient(
            uri,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
            socketTimeoutMS=5000,
            timeoutMS=5000,
            tlsCAFile=certifi.where(),
            retryWrites=True,
            w="majority",
        )
        self.db = self.client.get_database("firmly")
        self.jobs = self.db.jobs
        self.reports = self.db.reports

    def create_job(self, job_id: str, inputs: dict[str, Any]) -> None:
        """Create a new research job record."""
        self.jobs.update_one(
            {"job_id": job_id},
            {
                "$setOnInsert": {
                    "job_id": job_id,
                    "inputs": inputs,
                    "status": "pending",
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                }
            },
            upsert=True,
        )

    def update_job(
        self,
        job_id: str,
        status: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Update a research job with results or status."""
        update_data = {"updated_at": datetime.now(UTC)}
        if status:
            update_data["status"] = status
        if result:
            update_data["result"] = result
        if error:
            update_data["error"] = error

        self.jobs.update_one({"job_id": job_id}, {"$set": update_data})

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Retrieve a job by ID."""
        return self.jobs.find_one({"job_id": job_id})

    def store_report(self, job_id: str, report_data: dict[str, Any]) -> bool:
        """Store the finalized research report."""
        self.reports.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "job_id": job_id,
                    "report_content": report_data.get("report", ""),
                    "references": report_data.get("references", []),
                    "sections": report_data.get("sections_completed", []),
                    "research_queries": report_data.get("research_queries", {}),
                    "created_at": datetime.now(UTC),
                }
            },
            upsert=True,
        )
        return True

    def get_report(self, job_id: str) -> dict[str, Any] | None:
        """Retrieve a report by job ID."""
        return self.reports.find_one({"job_id": job_id})

    def close(self) -> None:
        self.client.close()
