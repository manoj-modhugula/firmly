# Changes: module organization, naming, and safe diagnostics.
import asyncio
import logging

from langchain_core.messages import AIMessage

from ..connections import open_web_connection
from ..jobs import publish_event
from ..schemas import ResearchContext

logger = logging.getLogger(__name__)


class SourceReadingStage:
    """Enriches curated documents with raw content."""

    def __init__(self, search_key: str | None = None) -> None:
        self.web_connection = open_web_connection(search_key)
        self.extract_limit = asyncio.Semaphore(3)

    async def fetch_single_content(self, url: str) -> dict[str, str]:
        """Fetch raw content for a single URL."""
        try:
            async with self.extract_limit:
                result = await self.web_connection.extract(url, extract_depth="advanced")
            if result and result.get("results"):
                return {url: result["results"][0].get("raw_content", "")}
        except Exception as e:
            logger.error("Error fetching raw content for %s: %s", url, type(e).__name__)
            return {url: ""}
        return {url: ""}

    async def fetch_raw_content(self, urls: list[str], on_enriched=None) -> dict[str, str]:
        """Fetch raw content for multiple URLs in parallel with rate limiting.

        on_enriched is called each time a URL returns non-empty content.
        """

        async def fetch_and_report(url: str) -> dict[str, str]:
            result = await self.fetch_single_content(url)
            if on_enriched and result.get(url):
                on_enriched()
            return result

        results = await asyncio.gather(*(fetch_and_report(url) for url in dict.fromkeys(urls)))
        return {url: content for result in results for url, content in result.items()}

    async def enrich_data(self, state: ResearchContext) -> ResearchContext:
        """Enrich curated documents with raw content."""
        company = state.get("company", "Unknown Company")
        job_id = state.get("job_id")

        logger.info("Starting enrichment for company: %s, job_id=%s", company, job_id)
        msg = [f"📚 Enriching curated data for {company}:"]

        # Process each type of curated data
        data_types = {
            "financial_data": "💰 Financial",
            "news_data": "📰 News",
            "industry_data": "🏭 Industry",
            "company_data": "🏢 Company",
        }

        # Create tasks for parallel processing
        enrichment_tasks = []
        for data_field, label in data_types.items():
            curated_field = f"curated_{data_field}"
            curated_docs = state.get(curated_field, {})

            if not curated_docs:
                msg.append(f"\n• No curated {label} documents to enrich")
                continue

            # Find documents needing enrichment
            docs_needing_content = {
                url: doc for url, doc in curated_docs.items() if not doc.get("raw_content")
            }

            if not docs_needing_content:
                msg.append(f"\n• All {label} documents already have raw content")
                continue

            msg.append(f"\n• Enriching {len(docs_needing_content)} {label} documents...")

            # Extract category name from field (e.g., 'curated_financial_data' -> 'financial')
            category = curated_field.replace("curated_", "").replace("_data", "")

            enrichment_tasks.append(
                {
                    "field": curated_field,
                    "label": label,
                    "category": category,
                    "docs": docs_needing_content,
                    "curated_docs": curated_docs,
                }
            )

        # Emit enrichment start event
        if enrichment_tasks:
            publish_event(
                job_id,
                {"type": "enrichment", "message": f"Enriching {len(enrichment_tasks)} categories"},
            )

        # Process all categories in parallel
        if enrichment_tasks:

            async def process_category(task):
                try:
                    progress = {"enriched": 0}
                    total = len(task["docs"])

                    def report_progress():
                        # Stream per-document progress so the UI counts up as extracts land
                        progress["enriched"] += 1
                        publish_event(
                            job_id,
                            {
                                "type": "enrichment",
                                "category": task["category"],
                                "enriched": progress["enriched"],
                                "total": total,
                                "message": f"Enriched {progress['enriched']}/{total} {task['label']} documents",
                            },
                        )

                    raw_contents = await self.fetch_raw_content(
                        list(task["docs"].keys()), report_progress
                    )

                    enriched_count = 0
                    for url, content in raw_contents.items():
                        if content:  # Only add non-empty content
                            task["curated_docs"][url]["raw_content"] = content
                            enriched_count += 1

                    # Update state with enriched documents
                    state[task["field"]] = task["curated_docs"]

                    return {
                        "label": task["label"],
                        "category": task["category"],
                        "enriched": enriched_count,
                        "total": len(task["docs"]),
                    }
                except Exception as e:
                    logger.error(
                        "Error processing category %s: %s", task["label"], type(e).__name__
                    )
                    return {
                        "label": task["label"],
                        "category": task["category"],
                        "enriched": 0,
                        "total": len(task["docs"]),
                    }

            # Process all categories in parallel
            results = await asyncio.gather(*[process_category(task) for task in enrichment_tasks])

            # Add summary to message and emit enrichment completion events
            for result in results:
                msg.append(
                    f"\n  ✓ {result['label']}: {result['enriched']}/{result['total']} documents enriched"
                )

                # Emit enrichment completion event for each category
                publish_event(
                    job_id,
                    {
                        "type": "enrichment",
                        "category": result["category"],
                        "enriched": result["enriched"],
                        "total": result["total"],
                        "message": f"Enriched {result['enriched']}/{result['total']} {result['label']} documents",
                    },
                )

        # Update state with enrichment message
        state.setdefault("messages", []).append(AIMessage(content="\n".join(msg)))

        return state

    async def run(self, state: ResearchContext) -> ResearchContext:
        try:
            return await self.enrich_data(state)
        except Exception as e:
            logger.error("Error in enrichment process: %s", type(e).__name__)
            return state
