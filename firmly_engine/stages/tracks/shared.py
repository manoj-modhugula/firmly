# Changes: module organization, naming, and safe diagnostics.
import asyncio
import logging
from datetime import datetime
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from ...connections import open_web_connection
from ...formatting.references import clean_title
from ...instructions import SEARCH_OUTPUT_RULES
from ...jobs import publish_event
from ...models import ModelSettings, create_research_model
from ...schemas import ResearchContext

logger = logging.getLogger(__name__)


class ResearchTrack:
    def __init__(self, search_key: str | None = None, llm_config: ModelSettings | None = None):
        self.web_connection = open_web_connection(search_key)
        self.llm = create_research_model("research", llm_config, streaming=True)
        self.track_id = "unassigned"

    @property
    def track_id(self) -> str:
        if not hasattr(self, "_track_id"):
            raise ValueError("track type not set by subclass")
        return self._track_id

    @track_id.setter
    def track_id(self, value: str):
        self._track_id = value

    async def generate_queries(self, state: dict, prompt: str):
        """Generate search queries and yield events as they're created"""
        company = state.get("company", "Unknown Company")
        industry = state.get("industry", "Unknown Industry")
        hq_location = state.get("hq_location", "Unknown")
        current_year = datetime.now().year
        job_id = state.get("job_id")

        try:
            logger.info(
                "Generating queries for %s as %s, job_id=%s", company, self.track_id, job_id
            )

            # Create prompt template using LangChain
            query_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are researching {company}, a company in the {industry} industry, headquartered in {hq_location}. Website context: {company_url}. Distinguish this company from similarly named organizations.",
                    ),
                    (
                        "user",
                        """Researching {company} in {year}, as of {date}.
{task_prompt}
{format_guidelines}""",
                    ),
                ]
            )

            # Create LCEL chain
            chain = query_prompt | self.llm

            queries = []
            current_query = ""
            current_query_number = 1

            # Stream queries using LangChain's astream
            async for chunk in chain.astream(
                {
                    "company": company,
                    "industry": industry,
                    "hq_location": hq_location,
                    "company_url": state.get("company_url") or "Not supplied",
                    "year": current_year,
                    "date": datetime.now().strftime("%B %d, %Y"),
                    "task_prompt": prompt.format(
                        company=company, industry=industry, hq_location=hq_location
                    ),
                    "format_guidelines": SEARCH_OUTPUT_RULES.format(company=company),
                }
            ):
                current_query += chunk.content

                # Yield query generation progress
                event = {
                    "type": "query_generating",
                    "query": current_query,
                    "query_number": current_query_number,
                    "category": self.track_id,
                }

                # Update job status if job_id provided
                publish_event(job_id, event)

                yield event

                # Parse completed queries on newline
                if "\n" in current_query:
                    parts = current_query.split("\n")
                    current_query = parts[-1]

                    for query in parts[:-1]:
                        query = query.strip()
                        if query:
                            queries.append(query)
                            event = {
                                "type": "query_generated",
                                "query": query,
                                "query_number": len(queries),
                                "category": self.track_id,
                            }

                            # Update job status if job_id provided
                            publish_event(job_id, event)

                            yield event
                            current_query_number += 1

            # Add remaining query
            if current_query.strip():
                queries.append(current_query.strip())
                event = {
                    "type": "query_generated",
                    "query": current_query.strip(),
                    "query_number": len(queries),
                    "category": self.track_id,
                }
                publish_event(job_id, event)
                yield event

            if not queries:
                raise ValueError(f"No queries generated for {company}")

            queries = queries[:2]  # Fast mode: two focused queries per track
            logger.debug("Generated %s queries for %s", len(queries), self.track_id)

            yield {"type": "queries_complete", "queries": queries, "count": len(queries)}

        except Exception as e:
            logger.error("Error generating queries for %s: %s", company, type(e).__name__)
            raise RuntimeError(
                f"Fatal API error - query generation failed: {type(e).__name__}"
            ) from e

    def _get_search_params(self) -> dict[str, Any]:
        """Get search parameters based on track type"""
        params = {"search_depth": "advanced", "include_raw_content": False, "max_results": 3}

        topic_map = {"news": "news", "financial": "finance"}

        if topic := topic_map.get(self.track_id):
            params["topic"] = topic

        return params

    def _process_search_result(self, result: dict[str, Any], query: str) -> dict[str, Any]:
        """Process a single search result into standardized format"""
        if not result.get("content") or not result.get("url"):
            return {}

        url = result.get("url")
        title = clean_title(result.get("title", "")) if result.get("title") else ""

        # Reset empty or invalid titles
        if not title or title.lower() == url.lower():
            title = ""

        return {
            "title": title,
            "content": result.get("content", ""),
            "query": query,
            "url": url,
            "source": "web_search",
            "score": result.get("score", 0.0),
        }

    async def search_documents(self, state: ResearchContext, queries: list[str]):
        """Execute all web research searches in parallel and yield events"""
        if not queries:
            logger.error("No valid queries to search")
            yield {"type": "error", "error": "No valid queries to search"}
            return

        # Yield start event
        yield {
            "type": "search_started",
            "message": f"Searching {len(queries)} queries",
            "total_queries": len(queries),
        }

        # Execute all searches in parallel
        search_params = self._get_search_params()
        search_tasks = [self.web_connection.search(query, **search_params) for query in queries]

        try:
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
        except Exception as e:
            logger.error("Error during parallel search execution: %s", type(e).__name__)
            yield {"type": "error", "error": "Source search unavailable"}
            return

        # Process and merge results
        merged_docs = {}
        for query, result in zip(queries, results):
            if isinstance(result, Exception):
                logger.error("Source search failed (%s)", type(result).__name__)
                yield {"type": "query_error", "query": query, "error": "Source search unavailable"}
                continue

            for item in result.get("results", []):
                if doc := self._process_search_result(item, query):
                    merged_docs[doc["url"]] = doc

        # Yield completion event
        yield {
            "type": "search_complete",
            "message": f"Found {len(merged_docs)} documents",
            "total_documents": len(merged_docs),
            "queries_processed": len(queries),
            "merged_docs": merged_docs,
        }

    async def run(self, state: ResearchContext):
        async for event in self.analyze(state):
            yield event
