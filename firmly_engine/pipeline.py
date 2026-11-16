# Changes: state preservation and parallel-node adapters.
import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph

from .jobs import publish_event
from .models import ModelSettings
from .schemas.state import CompanyInput, ResearchContext
from .stages import CompanyContextStage
from .stages.compose import ReportAssemblyStage
from .stages.gather import SourceGatheringStage
from .stages.rank import SourceSelectionStage
from .stages.retrieve import SourceReadingStage
from .stages.summarize import SectionWritingStage
from .stages.tracks import (
    CompanyTrack,
    FinancialTrack,
    MarketTrack,
    NewsTrack,
)

logger = logging.getLogger(__name__)


class ResearchPipeline:
    def __init__(
        self,
        company=None,
        url=None,
        hq_location=None,
        industry=None,
        job_id=None,
        search_key=None,
        model_key=None,
        model=None,
    ):
        self.search_key = search_key
        self.llm_config = ModelSettings.resolve(model_key, model)
        # Initialize CompanyInput
        self.input_state = CompanyInput(
            company=company,
            company_url=url,
            hq_location=hq_location,
            industry=industry,
            job_id=job_id,
            messages=[
                SystemMessage(content="Firmly is gathering evidence about the selected company.")
            ],
        )

        # Initialize nodes
        self._initialize_stages()
        self._connect_stages()

    def _initialize_stages(self):
        """Initialize all workflow nodes"""
        self.context_stage = CompanyContextStage()
        self.financial_track = FinancialTrack(self.search_key, self.llm_config)
        self.news_track = NewsTrack(self.search_key, self.llm_config)
        self.market_track = MarketTrack(self.search_key, self.llm_config)
        self.company_track = CompanyTrack(self.search_key, self.llm_config)
        self.gather_stage = SourceGatheringStage()
        self.selection_stage = SourceSelectionStage()
        self.reading_stage = SourceReadingStage(self.search_key)
        self.writing_stage = SectionWritingStage(self.llm_config)
        self.assembly_stage = ReportAssemblyStage(self.llm_config)

    def _run_track(self, researcher, field):
        """Firmly: convert research event generators into disjoint graph updates."""

        async def run(state):
            isolated = dict(state, messages=list(state.get("messages", [])))
            documents = {}
            async for event in researcher.run(isolated):
                if not isinstance(event, dict):
                    continue
                if field in event:
                    documents = event[field]
                kind = event.get("type")
                # Query events already enter the shared queue in ResearchTrack.
                if kind and kind not in {"query_generating", "query_generated", "queries_complete"}:
                    publish_event(state.get("job_id"), dict(event, category=researcher.track_id))
            return {field: documents}

        return run

    def _connect_stages(self):
        """Configure the state graph workflow"""
        self.workflow = StateGraph(ResearchContext)

        # Add nodes with their respective processing functions
        self.workflow.add_node("company_context", self.context_stage.run)
        self.workflow.add_node(
            "financial_track", self._run_track(self.financial_track, "financial_data")
        )
        self.workflow.add_node("news_track", self._run_track(self.news_track, "news_data"))
        self.workflow.add_node("market_track", self._run_track(self.market_track, "industry_data"))
        self.workflow.add_node("company_track", self._run_track(self.company_track, "company_data"))
        self.workflow.add_node("gather_stage", self.gather_stage.run)
        self.workflow.add_node("selection_stage", self.selection_stage.run)
        self.workflow.add_node("reading_stage", self.reading_stage.run)
        self.workflow.add_node("writing_stage", self.writing_stage.run)
        self.workflow.add_node("assembly_stage", self.assembly_stage.run)

        # Configure workflow edges
        self.workflow.set_entry_point("company_context")
        self.workflow.set_finish_point("assembly_stage")

        research_nodes = ["financial_track", "news_track", "market_track", "company_track"]

        # Connect grounding to all research nodes
        for node in research_nodes:
            self.workflow.add_edge("company_context", node)

        self.workflow.add_edge(research_nodes, "gather_stage")

        # Connect remaining nodes
        self.workflow.add_edge("gather_stage", "selection_stage")
        self.workflow.add_edge("selection_stage", "reading_stage")
        self.workflow.add_edge("reading_stage", "writing_stage")
        self.workflow.add_edge("writing_stage", "assembly_stage")

    async def run(self, thread: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        """Execute the research workflow"""
        compiled_graph = self.workflow.compile()

        async for state in compiled_graph.astream(self.input_state, thread):
            yield state

    def compile(self):
        graph = self.workflow.compile()
        return graph
