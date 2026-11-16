# Changes: module organization, naming, and safe diagnostics.
from langchain_core.messages import AIMessage

from ...instructions import MARKET_SEARCH_INSTRUCTIONS
from ...models import ModelSettings
from ...schemas import ResearchContext
from .shared import ResearchTrack


class MarketTrack(ResearchTrack):
    def __init__(
        self, search_key: str | None = None, llm_config: ModelSettings | None = None
    ) -> None:
        super().__init__(search_key, llm_config)
        self.track_id = "industry"

    async def analyze(self, state: ResearchContext):
        """Analyze industry and yield events"""
        company = state.get("company", "Unknown Company")
        industry = state.get("industry", "Unknown Industry")

        # Generate search queries and yield events
        queries = []
        async for event in self.generate_queries(state, MARKET_SEARCH_INSTRUCTIONS):
            yield event
            if event.get("type") == "queries_complete":
                queries = event.get("queries", [])

        # Log subqueries
        subqueries_msg = "🔍 Subqueries for industry analysis:\n" + "\n".join(
            [f"• {query}" for query in queries]
        )
        state.setdefault("messages", []).append(AIMessage(content=subqueries_msg))

        # Start with site scrape data
        industry_data = dict(state.get("site_scrape", {}))

        # Search and merge documents, yielding events
        documents = {}
        async for event in self.search_documents(state, queries):
            yield event
            if event.get("type") == "search_complete":
                documents = event.get("merged_docs", {})

        industry_data.update(documents)

        # Update state
        completion_msg = (
            f"🏭 Market research found {len(industry_data)} documents for {company} in {industry}"
        )
        state.setdefault("messages", []).append(AIMessage(content=completion_msg))
        state["industry_data"] = industry_data

        yield {
            "type": "analysis_complete",
            "data_type": "industry_data",
            "count": len(industry_data),
        }
        yield {"message": [completion_msg], "industry_data": industry_data}
