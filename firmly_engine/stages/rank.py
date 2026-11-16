# Changes: module organization, naming, and safe diagnostics.
import logging

from langchain_core.messages import AIMessage

from ..formatting.references import normalize_url, process_references_from_search_results
from ..jobs import publish_event
from ..schemas import ResearchContext

logger = logging.getLogger(__name__)


class SourceSelectionStage:
    def __init__(self) -> None:
        self.relevance_threshold = 0.4
        logger.info(
            "SourceSelectionStage initialized with relevance threshold: %s",
            self.relevance_threshold,
        )

    def evaluate_documents(self, docs: list, context: dict[str, str]) -> list:
        """Evaluate documents based on source relevance scores."""
        if not docs:
            return []

        logger.info("Evaluating %s documents", len(docs))

        evaluated_docs = []
        try:
            # Evaluate each document using source relevance scores
            for doc in docs:
                try:
                    # Ensure score is a valid float
                    relevance_score = float(doc.get("score", 0))  # Default to 0 if no score

                    # Always keep company website data regardless of score (first-party information)
                    is_company_website = doc.get("source") == "company_website"

                    # Keep documents with good source relevance scores or company website data
                    if relevance_score >= self.relevance_threshold or is_company_website:
                        reason = (
                            "company website"
                            if is_company_website
                            else f"score {relevance_score:.4f}"
                        )
                        logger.info(
                            "Document kept (%s) for '%s')", reason, doc.get("title", "No title")
                        )

                        evaluated_doc = {
                            **doc,
                            "evaluation": {
                                "overall_score": relevance_score,  # Store as float
                                "query": doc.get("query", ""),
                            },
                        }
                        evaluated_docs.append(evaluated_doc)
                    else:
                        logger.info(
                            f"Document below threshold with score {relevance_score:.4f} for '{doc.get('title', 'No title')}'"
                        )
                except (ValueError, TypeError) as e:
                    logger.warning("Error processing score for document: %s", type(e).__name__)
                    continue

        except Exception as e:
            logger.error("Error during document evaluation: %s", type(e).__name__)
            return []

        # Sort evaluated docs by score before returning
        evaluated_docs.sort(key=lambda x: float(x["evaluation"]["overall_score"]), reverse=True)
        logger.info("Returning %s evaluated documents", len(evaluated_docs))

        return evaluated_docs

    async def curate_data(self, state: ResearchContext) -> ResearchContext:
        """Curate all collected data based on source relevance scores."""
        company = state.get("company", "Unknown Company")
        job_id = state.get("job_id")
        logger.info("Starting curation for company: %s, job_id=%s", company, job_id)

        industry = state.get("industry", "Unknown")
        context = {
            "company": company,
            "industry": industry,
            "hq_location": state.get("hq_location", "Unknown"),
        }

        msg = [f"🔍 Curating research data for {company}"]

        data_types = {
            "financial_data": ("💰 Financial", "financial"),
            "news_data": ("📰 News", "news"),
            "industry_data": ("🏭 Industry", "industry"),
            "company_data": ("🏢 Company", "company"),
        }

        # Process each data type
        for data_field, (emoji, doc_type) in data_types.items():
            data = state.get(data_field, {})
            if not data:
                continue

            # Filter and normalize URLs
            unique_docs = {}
            for url, doc in data.items():
                try:
                    clean_url = normalize_url(url)
                    if not clean_url:
                        continue
                    if clean_url not in unique_docs:
                        doc["url"] = clean_url
                        doc["doc_type"] = doc_type
                        unique_docs[clean_url] = doc
                except Exception:
                    continue

            docs = list(unique_docs.values())
            msg.append(f"\n{emoji}: Found {len(docs)} documents")

            evaluated_docs = self.evaluate_documents(docs, context)

            # Emit curation event with total count
            publish_event(
                job_id,
                {
                    "type": "curation",
                    "category": doc_type,
                    "total": len(evaluated_docs) if evaluated_docs else 0,
                    "message": f"Curating {doc_type} documents",
                },
            )

            if not evaluated_docs:
                msg.append("  ⚠️ No relevant documents found")
                continue

            # Filter and sort by source relevance scores
            relevant_docs = {doc["url"]: doc for doc in evaluated_docs}
            sorted_items = sorted(
                relevant_docs.items(),
                key=lambda item: item[1]["evaluation"]["overall_score"],
                reverse=True,
            )

            # Fast mode: enrich only the strongest sources in each category.
            if len(sorted_items) > 5:
                sorted_items = sorted_items[:5]
            relevant_docs = dict(sorted_items)

            if relevant_docs:
                msg.append(f"  ✓ Kept {len(relevant_docs)} relevant documents")
                logger.info(
                    "Kept %s documents for %s with scores above threshold",
                    len(relevant_docs),
                    doc_type,
                )
            else:
                msg.append("  ⚠️ No documents met relevance threshold")
                logger.info("No documents met relevance threshold for %s", doc_type)

            # Store curated documents in state
            state[f"curated_{data_field}"] = relevant_docs

        # Process references using the references module
        top_reference_urls, reference_titles, reference_info = (
            process_references_from_search_results(state)
        )
        logger.info("Selected top %s references for the report", len(top_reference_urls))

        # Update state with references and their titles
        state.setdefault("messages", []).append(AIMessage(content="\n".join(msg)))
        state["references"] = top_reference_urls
        state["reference_titles"] = reference_titles
        state["reference_info"] = reference_info

        return state

    async def run(self, state: ResearchContext) -> ResearchContext:
        return await self.curate_data(state)
