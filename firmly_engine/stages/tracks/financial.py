# Changes: module organization, naming, and safe diagnostics.
from langchain_core.messages import AIMessage

from ...instructions import FINANCIAL_SEARCH_INSTRUCTIONS
from ...models import ModelSettings
from ...schemas import ResearchContext
from .shared import ResearchTrack


class FinancialTrack(ResearchTrack):
    def __init__(
        self, search_key: str | None = None, llm_config: ModelSettings | None = None
    ) -> None:
        super().__init__(search_key, llm_config)
        self.track_id = "financial"

    async def analyze(self, state: ResearchContext):
        """Analyze financials and yield events"""
        company = state.get("company", "Unknown Company")

        # Generate search queries and yield events
        queries = []
        async for event in self.generate_queries(state, FINANCIAL_SEARCH_INSTRUCTIONS):
            yield event
            if event.get("type") == "queries_complete":
                queries = event.get("queries", [])

        # Log subqueries
        subqueries_msg = "🔍 Subqueries for financial analysis:\n" + "\n".join(
            [f"• {query}" for query in queries]
        )
        state.setdefault("messages", []).append(AIMessage(content=subqueries_msg))

        # Start with site scrape data
        financial_data = dict(state.get("site_scrape", {}))

        # Search and merge documents, yielding events
        documents = {}
        async for event in self.search_documents(state, queries):
            yield event
            if event.get("type") == "search_complete":
                documents = event.get("merged_docs", {})

        financial_data.update(documents)

        # Update state
        completion_msg = (
            f"💰 Financial research found {len(financial_data)} documents for {company}"
        )
        state.setdefault("messages", []).append(AIMessage(content=completion_msg))
        state["financial_data"] = financial_data

        yield {
            "type": "analysis_complete",
            "data_type": "financial_data",
            "count": len(financial_data),
        }
        yield {"message": [completion_msg], "financial_data": financial_data}
