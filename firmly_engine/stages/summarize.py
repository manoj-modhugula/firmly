# Changes: retain source URLs in briefing context.
import asyncio
import logging
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ..concurrency import gather_tasks
from ..instructions import (
    COMPANY_SECTION_INSTRUCTIONS,
    FINANCIAL_SECTION_INSTRUCTIONS,
    MARKET_SECTION_INSTRUCTIONS,
    NEWS_SECTION_INSTRUCTIONS,
    SOURCE_READING_RULES,
)
from ..jobs import publish_event
from ..models import ModelSettings, create_research_model
from ..schemas import ResearchContext

logger = logging.getLogger(__name__)


class SectionWritingStage:
    """Creates briefings for each research category and updates the ResearchContext."""

    def __init__(self, llm_config: ModelSettings | None = None) -> None:
        self.max_doc_length = 8000  # Maximum document content length
        self.llm = create_research_model("briefing", llm_config)

    def _get_category_prompt(self, category: str) -> str:
        """Get the category-specific prompt template"""
        prompts = {
            "company": COMPANY_SECTION_INSTRUCTIONS,
            "industry": MARKET_SECTION_INSTRUCTIONS,
            "financial": FINANCIAL_SECTION_INSTRUCTIONS,
            "news": NEWS_SECTION_INSTRUCTIONS,
        }
        return prompts.get(
            category,
            "Create a focused, informative and insightful research briefing on the company: {company} in the {industry} industry based on the provided documents.",
        )

    def _prepare_documents(self, docs: dict[str, Any] | list[dict[str, Any]]) -> str:
        """Prepare and format documents for briefing generation"""
        # Normalize docs to list of (url, doc) tuples
        items = (
            list(docs.items())
            if isinstance(docs, dict)
            else [(doc.get("url", f"doc_{i}"), doc) for i, doc in enumerate(docs)]
        )

        # Sort by evaluation score
        sorted_items = sorted(
            items,
            key=lambda x: float(x[1].get("evaluation", {}).get("overall_score", "0")),
            reverse=True,
        )

        # Format documents with length limits
        doc_texts = []
        total_length = 0
        for _, doc in sorted_items:
            title = doc.get("title", "")
            content = doc.get("raw_content") or doc.get("content", "")

            if len(content) > self.max_doc_length:
                content = content[: self.max_doc_length] + "... [content truncated]"

            doc_entry = f"Title: {title}\nURL: {doc.get('url') or _}\n\nContent: {content}"
            if total_length + len(doc_entry) < 120000:  # Keep under limit
                doc_texts.append(doc_entry)
                total_length += len(doc_entry)
            else:
                break

        separator = "\n" + "-" * 40 + "\n"
        return f"{separator}{separator.join(doc_texts)}{separator}"

    async def generate_category_briefing(
        self, docs: dict[str, Any] | list[dict[str, Any]], category: str, context: dict[str, Any]
    ):
        """Generate category briefing and yield events"""
        company = context.get("company", "Unknown")
        industry = context.get("industry", "Unknown")
        hq_location = context.get("hq_location", "Unknown")
        job_id = context.get("job_id")

        logger.info(
            "Generating %s briefing for %s using %s documents", category, company, len(docs)
        )

        # Emit briefing start event
        event = {
            "type": "briefing_start",
            "category": category,
            "total_docs": len(docs),
            "step": "SectionWritingStage",
        }

        publish_event(job_id, event)

        yield event

        # Get category-specific prompt and prepare documents
        category_prompt = self._get_category_prompt(category).format(
            company=company, industry=industry, hq_location=hq_location
        )
        formatted_docs = self._prepare_documents(docs)

        # Create LCEL chain for briefing generation
        briefing_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "user",
                    """{category_prompt}

{instruction}

{documents}""",
                )
            ]
        )

        chain = briefing_prompt | self.llm | StrOutputParser()

        try:
            logger.info("Sending prompt to LLM")
            content = await chain.ainvoke(
                {
                    "category_prompt": category_prompt,
                    "instruction": SOURCE_READING_RULES,
                    "documents": formatted_docs,
                }
            )

            if not content:
                logger.error("Empty response from LLM for %s briefing", category)
                yield {"type": "error", "error": "Empty response from LLM", "category": category}
                yield {"content": ""}
                return

            # Emit completion event
            event = {
                "type": "briefing_complete",
                "category": category,
                "content_length": len(content),
                "step": "SectionWritingStage",
            }

            publish_event(job_id, event)

            yield event
            yield {"content": content.strip()}
        except Exception as e:
            logger.error("Error generating %s briefing: %s", category, type(e).__name__)
            raise RuntimeError(
                f"Fatal API error - {category} briefing generation failed: {type(e).__name__}"
            ) from e

    async def create_briefings(self, state: ResearchContext) -> ResearchContext:
        """Create briefings for all categories in parallel."""
        company = state.get("company", "Unknown Company")
        logger.info("Creating section briefings for %s", company)

        context = {
            "company": company,
            "industry": state.get("industry", "Unknown"),
            "hq_location": state.get("hq_location", "Unknown"),
            "job_id": state.get("job_id"),
        }

        # Mapping of curated data fields to briefing categories
        categories = {
            "financial_data": ("financial", "financial_briefing"),
            "news_data": ("news", "news_briefing"),
            "industry_data": ("industry", "industry_briefing"),
            "company_data": ("company", "company_briefing"),
        }

        briefings = {}

        # Create tasks for parallel processing
        briefing_tasks = []
        for data_field, (cat, briefing_key) in categories.items():
            curated_key = f"curated_{data_field}"
            curated_data = state.get(curated_key, {})

            if curated_data:
                logger.info("Processing %s with %s documents", data_field, len(curated_data))
                briefing_tasks.append(
                    {
                        "category": cat,
                        "briefing_key": briefing_key,
                        "data_field": data_field,
                        "curated_data": curated_data,
                    }
                )
            else:
                logger.info("No data available for %s", data_field)
                state[briefing_key] = ""

        # Process briefings in parallel with rate limiting
        if briefing_tasks:
            briefing_semaphore = asyncio.Semaphore(2)  # Limit to 2 concurrent briefings

            async def process_briefing(task: dict[str, Any]) -> dict[str, Any]:
                """Process a single briefing with rate limiting."""
                async with briefing_semaphore:
                    result = {"content": ""}

                    # Consume events from briefing generation
                    # Exceptions will propagate immediately (no catching)
                    async for event in self.generate_category_briefing(
                        task["curated_data"], task["category"], context
                    ):
                        if isinstance(event, dict) and "content" in event:
                            result = event

                    if result["content"]:
                        briefings[task["category"]] = result["content"]
                        state[task["briefing_key"]] = result["content"]
                        logger.info(
                            "Completed %s briefing (%s characters)",
                            task["data_field"],
                            len(result["content"]),
                        )
                    else:
                        raise RuntimeError(f"Empty briefing generated for {task['data_field']}")

                    return {
                        "category": task["category"],
                        "success": bool(result["content"]),
                        "length": len(result["content"]) if result["content"] else 0,
                    }

            # Process all briefings in parallel - exceptions will propagate and kill entire process
            results = await gather_tasks(*(process_briefing(task) for task in briefing_tasks))

            # Log completion statistics
            successful_briefings = sum(1 for r in results if r["success"])
            total_length = sum(r["length"] for r in results)
            logger.info(
                "Generated %s/%s briefings with total length %s",
                successful_briefings,
                len(briefing_tasks),
                total_length,
            )

        state["briefings"] = briefings
        return state

    async def run(self, state: ResearchContext) -> ResearchContext:
        return await self.create_briefings(state)
