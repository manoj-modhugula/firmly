# Changes: module organization, naming, and safe diagnostics.
import logging

from langchain_core.messages import AIMessage

from ..jobs import publish_event
from ..schemas import CompanyInput, ResearchContext

logger = logging.getLogger(__name__)


class CompanyContextStage:
    """Gathers initial grounding data about the company."""

    async def initial_search(self, state: CompanyInput):
        """Initial search and yield events"""
        company = state.get("company", "Unknown Company")
        job_id = state.get("job_id")
        msg = f"🎯 Initiating research for {company}...\n"

        # Emit initialization event
        event = {
            "type": "research_init",
            "company": company,
            "message": f"Initiating research for {company}",
            "step": "Initializing",
        }

        publish_event(job_id, event)

        yield event

        # Fast mode relies on targeted search and skips the potentially large
        # company-site crawl. The submitted URL is retained in the job state.
        site_scrape = {}
        # Add context about what information we have
        if hq := state.get("hq_location"):
            msg += f"\n📍 Company HQ: {hq}"
        if industry := state.get("industry"):
            msg += f"\n🏭 Industry: {industry}"

        # Initialize ResearchContext with input information
        research_state = {
            # Copy input fields
            "company": state.get("company"),
            "company_url": state.get("company_url"),
            "hq_location": state.get("hq_location"),
            "industry": state.get("industry"),
            "job_id": state.get("job_id"),
            # Initialize research fields
            "messages": [AIMessage(content=msg)],
            "site_scrape": site_scrape,
        }

        yield {"type": "grounding_complete", "site_pages": len(site_scrape)}
        yield research_state

    async def run(self, state: CompanyInput) -> ResearchContext:
        """Return grounded company context after publishing initialization progress."""
        result = None
        async for event in self.initial_search(state):
            # The last yield should be the research_state (a dict with state fields)
            # Earlier yields are event dicts with "type" field
            if isinstance(event, dict) and "type" not in event:
                result = event
        return result if result else {}
