# Changes: preserve reference metadata in graph state.
from typing import Any, NotRequired, Required, TypedDict


# Define the input state
class CompanyInput(TypedDict, total=False):
    company: Required[str]
    company_url: NotRequired[str]
    hq_location: NotRequired[str]
    industry: NotRequired[str]
    job_id: NotRequired[str]


class ResearchContext(CompanyInput):
    site_scrape: dict[str, Any]
    messages: list[Any]
    financial_data: dict[str, Any]
    news_data: dict[str, Any]
    industry_data: dict[str, Any]
    company_data: dict[str, Any]
    curated_financial_data: dict[str, Any]
    curated_news_data: dict[str, Any]
    curated_industry_data: dict[str, Any]
    curated_company_data: dict[str, Any]
    financial_briefing: str
    news_briefing: str
    industry_briefing: str
    company_briefing: str
    references: list[str]
    briefings: dict[str, Any]
    report: str
    reference_info: dict[str, Any]
    reference_titles: dict[str, str]
    assembled_report: dict[str, Any]
    status: str
