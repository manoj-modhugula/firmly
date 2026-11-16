# Changes: module organization, naming, and safe diagnostics.
from langchain_core.messages import AIMessage

from ..schemas import ResearchContext


class SourceGatheringStage:
    """Collects and organizes all research data before curation."""

    async def collect(self, state: ResearchContext) -> ResearchContext:
        """Collect and verify all research data is present."""
        company = state.get("company", "Unknown Company")
        msg = [f"📦 Collecting research data for {company}:"]

        # Check each type of research data
        research_types = {
            "financial_data": "💰 Financial",
            "news_data": "📰 News",
            "industry_data": "🏭 Industry",
            "company_data": "🏢 Company",
        }

        for data_field, label in research_types.items():
            data = state.get(data_field, {})
            if data:
                msg.append(f"• {label}: {len(data)} documents collected")
            else:
                msg.append(f"• {label}: No data found")

        if not any(state.get(field) for field in research_types):
            raise ValueError("No research sources were retrieved")

        # Update state with collection message
        state.setdefault("messages", []).append(AIMessage(content="\n".join(msg)))

        return state

    async def run(self, state: ResearchContext) -> ResearchContext:
        return await self.collect(state)
