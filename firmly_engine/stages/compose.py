# Changes: module organization, naming, and safe diagnostics.
import logging
import re

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ..formatting.references import format_references_section
from ..instructions import (
    REPORT_ASSEMBLY_INSTRUCTIONS,
    REPORT_ASSEMBLY_ROLE,
    REPORT_POLISH_INSTRUCTIONS,
    REPORT_POLISH_ROLE,
)
from ..jobs import publish_event
from ..models import ModelSettings, create_research_model
from ..schemas import ResearchContext

logger = logging.getLogger(__name__)


class ReportAssemblyStage:
    """Compiles individual section briefings into a cohesive final report."""

    def __init__(self, llm_config: ModelSettings | None = None) -> None:
        self.llm = create_research_model("report", llm_config, streaming=True)

        # Initialize context dictionary
        self.context = {
            "company": "Unknown Company",
            "industry": "Unknown",
            "hq_location": "Unknown",
        }

    async def compile_briefings(self, state: ResearchContext) -> ResearchContext:
        """Compile individual briefing categories from state into a final report."""
        company = state.get("company", "Unknown Company")
        job_id = state.get("job_id")

        # Update context with values from state
        self.context = {
            "company": company,
            "industry": state.get("industry", "Unknown"),
            "hq_location": state.get("hq_location", "Unknown"),
        }

        msg = [f"📑 Compiling final report for {company}..."]

        # Emit report compilation start event
        publish_event(
            job_id,
            {"type": "report_compilation", "message": f"Compiling final report for {company}"},
        )

        # Pull individual briefings from dedicated state keys
        briefing_keys = {
            "company": "company_briefing",
            "industry": "industry_briefing",
            "financial": "financial_briefing",
            "news": "news_briefing",
        }

        individual_briefings = {}
        for category, key in briefing_keys.items():
            if content := state.get(key):
                individual_briefings[category] = content
                msg.append(f"Found {category} briefing ({len(content)} characters)")
            else:
                msg.append(f"No {category} briefing available")
                logger.error("Missing state key: %s", key)

        if not individual_briefings:
            msg.append("\n⚠️ No briefing sections available to compile")
            logger.error("No briefings found in state")
        else:
            try:
                compiled_report = await self.edit_report(state, individual_briefings)
                if not compiled_report or not compiled_report.strip():
                    logger.error("Compiled report is empty!")
                else:
                    logger.info(
                        "Successfully compiled report with %s characters", len(compiled_report)
                    )
            except Exception as e:
                logger.error("Error during report compilation: %s", type(e).__name__)

        state.setdefault("messages", []).append(AIMessage(content="\n".join(msg)))
        return state

    async def edit_report(self, state: ResearchContext, briefings: dict[str, str]) -> str:
        """Compile section briefings into a final report and update the state."""
        try:
            logger.info("Starting report compilation")
            job_id = state.get("job_id")

            # Step 1: Initial Compilation
            edited_report = await self.compile_content(state, briefings)
            if not edited_report:
                logger.error("Initial compilation failed")
                return ""

            # Step 2 & 3: Content sweep and streaming
            final_report = ""
            async for event in self.content_sweep(edited_report):
                # Publish progress without exposing report chunks to the browser
                if isinstance(event, dict):
                    publish_event(job_id, event)

                # Accumulate the text
                if isinstance(event, str):
                    final_report = event

            final_report = final_report or edited_report or ""

            logger.info("Final report compiled with %s characters", len(final_report))
            if not final_report.strip():
                logger.error("Final report is empty!")
                return ""

            # Preserve the retrieved reference list outside the model rewrite.
            if state.get("references"):
                reference_text = format_references_section(
                    state["references"],
                    state.get("reference_info", {}),
                    state.get("reference_titles", {}),
                )
                final_report = (
                    re.split(
                        r"^##\s+(?:References|Sources)\s*$",
                        final_report,
                        flags=re.MULTILINE | re.IGNORECASE,
                    )[0].rstrip()
                    + "\n\n"
                    + reference_text.strip()
                )

            # Update state with the final report
            state["report"] = final_report
            state["status"] = "report_ready"
            if "assembled_report" not in state or not isinstance(state["assembled_report"], dict):
                state["assembled_report"] = {}
            state["assembled_report"]["report"] = final_report

            return final_report
        except Exception as e:
            logger.error("Error in edit_report: %s", type(e).__name__)
            return ""

    async def compile_content(self, state: ResearchContext, briefings: dict[str, str]) -> str:
        """Initial compilation of research sections using LCEL."""
        combined_content = "\n\n".join(content for content in briefings.values())

        references = state.get("references", [])
        reference_text = ""
        if references:
            logger.info("Found %s references to add during compilation", len(references))
            reference_info = state.get("reference_info", {})
            reference_titles = state.get("reference_titles", {})
            reference_text = format_references_section(references, reference_info, reference_titles)
            logger.info("Added %s references during compilation", len(references))

        # Create LCEL chain for compilation
        compile_prompt = ChatPromptTemplate.from_messages(
            [("system", REPORT_ASSEMBLY_ROLE), ("user", REPORT_ASSEMBLY_INSTRUCTIONS)]
        )

        chain = compile_prompt | self.llm | StrOutputParser()

        try:
            initial_report = await chain.ainvoke(
                {
                    "company": self.context["company"],
                    "industry": self.context["industry"],
                    "hq_location": self.context["hq_location"],
                    "combined_content": combined_content,
                }
            )

            # Append references section
            if reference_text:
                initial_report = f"{initial_report}\n\n{reference_text}"

            return initial_report
        except Exception as e:
            logger.error("Error in initial compilation: %s", type(e).__name__)
            return combined_content or ""

    async def content_sweep(self, content: str):
        """Sweep the content for any redundant information using LCEL streaming and yield events."""
        # Create LCEL chain for content sweep
        sweep_prompt = ChatPromptTemplate.from_messages(
            [("system", REPORT_POLISH_ROLE), ("user", REPORT_POLISH_INSTRUCTIONS)]
        )

        chain = sweep_prompt | self.llm | StrOutputParser()

        try:
            accumulated_text = ""
            buffer = ""

            # Stream using LangChain's astream
            async for chunk in chain.astream(
                {
                    "company": self.context["company"],
                    "industry": self.context["industry"],
                    "hq_location": self.context["hq_location"],
                    "content": content,
                }
            ):
                accumulated_text += chunk
                buffer += chunk

                # Yield chunks at sentence boundaries
                if any(char in buffer for char in [".", "!", "?", "\n"]) and len(buffer) > 10:
                    yield {"type": "report_chunk", "chunk": buffer, "step": "ReportAssemblyStage"}
                    buffer = ""

            # Yield final buffer
            if buffer:
                yield {"type": "report_chunk", "chunk": buffer, "step": "ReportAssemblyStage"}

            yield accumulated_text.strip()
        except Exception as e:
            logger.error("Error in formatting: %s", type(e).__name__)
            yield {
                "type": "error",
                "error": "Report formatting unavailable",
                "step": "ReportAssemblyStage",
            }
            yield content or ""

    async def run(self, state: ResearchContext) -> ResearchContext:
        state = await self.compile_briefings(state)
        # Ensure the ReportAssemblyStage node's output is stored both top-level and under "assembled_report"
        if "report" in state:
            if "assembled_report" not in state or not isinstance(state["assembled_report"], dict):
                state["assembled_report"] = {}
            state["assembled_report"]["report"] = state["report"]
        return state
