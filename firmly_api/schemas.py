"""Validated API request payloads."""

import uuid
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator


class ResearchRequest(BaseModel):
    request_id: uuid.UUID | None = None
    company: str = Field(min_length=1, max_length=180)
    company_url: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=180)
    hq_location: str | None = Field(default=None, max_length=180)
    search_key: str | None = Field(default=None, max_length=500, repr=False)
    model_key: str | None = Field(default=None, max_length=500, repr=False)
    model: str | None = Field(default=None, max_length=180)

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("company_url")
    @classmethod
    def website(cls, value):
        if not value:
            return None
        if urlsplit(value).scheme and "://" not in value:
            raise ValueError("Enter a valid HTTP or HTTPS website.")
        value = value if "://" in value else "https://" + value
        url = urlsplit(value)
        if url.scheme not in {"https", "http"} or not url.hostname or url.username or url.password:
            raise ValueError("Enter a valid company website without credentials.")
        return value


class PDFRequest(BaseModel):
    report_content: str = Field(min_length=1, max_length=500_000)
    company_name: str = Field(default="Company", min_length=1, max_length=180)
