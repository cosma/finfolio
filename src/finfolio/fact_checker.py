"""Core fact-checking logic with LangChain and Tavily integration."""

import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

from finfolio.config import Config
from finfolio.llm.cost_tracking import CostTrackingCallback
from finfolio.llm.prompts import get_verdict_prompt
from finfolio.models import ClaimModel, ReportModel, VerdictModel
from finfolio.search.tavily_client import TavilySearchClient

logger = logging.getLogger(__name__)


class FactChecker:
    """Main fact-checking orchestrator using LangChain + Tavily.

    Coordinates claim extraction, web search, LLM-based verdict reasoning,
    and report generation.
    """

    def __init__(self, config: Config):
        """Initialize FactChecker with configuration.

        Args:
            config: Configuration object with model, API keys, timeouts
        """
        self.config = config
        self.llm = self._get_llm()
        self.search_client = TavilySearchClient(
            api_key=config.tavily_api_key, timeout_seconds=config.search_timeout_seconds
        )
        self.cost_tracker = CostTrackingCallback()
        logger.info(f"FactChecker initialized with model: {config.llm_model}")

    def _get_llm(self):
        """Initialize LangChain LLM (ChatAnthropic).

        Returns:
            Initialized LLM instance with temperature=0
        """
        try:
            from langchain_anthropic import ChatAnthropic

            llm = ChatAnthropic(
                model=self.config.llm_model,
                temperature=0,  # Deterministic verdict reasoning
                api_key=self.config.anthropic_api_key,
            )
            logger.info(f"LLM initialized: {self.config.llm_model}")
            return llm
        except ImportError as e:
            logger.error(f"Failed to import ChatAnthropic: {str(e)}")
            raise

    def fact_check_claim(
        self, claim: ClaimModel, search_results: list[dict[str, Any]]
    ) -> VerdictModel:
        """Fact-check a single claim using LLM + search results.

        Args:
            claim: ClaimModel to fact-check
            search_results: List of search result dicts from Tavily

        Returns:
            VerdictModel with verdict, note, and source info
        """
        logger.info(f"Fact-checking claim {claim.id}: {claim.text[:50]}...")

        # Format search results for LLM
        formatted_results = self._format_search_results(search_results)

        # Generate prompt
        prompt = get_verdict_prompt(claim.text, formatted_results)

        # Call LLM for verdict reasoning
        response = self.llm.invoke(prompt)
        logger.debug(f"LLM response for {claim.id}: {response.content}")

        # Parse LLM response
        verdict_dict = self._parse_verdict_response(response.content)

        # Create VerdictModel
        verdict = VerdictModel(
            claim_id=claim.id,
            claim_text=claim.text,
            verdict=verdict_dict["verdict"],
            note=verdict_dict["note"],
            source_url=verdict_dict.get("source_url"),
            source_title=verdict_dict.get("source_title"),
            source_date=verdict_dict.get("source_date"),
            search_query=claim.text,  # Query used for search
            fact_checked_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            llm_model=self.config.llm_model,
            reasoning_cost={
                "tokens_in": 0,  # Would be populated by cost tracker
                "tokens_out": 0,
                "cost_usd": 0.0,
            },
        )

        logger.info(f"Verdict for {claim.id}: {verdict.verdict}")
        return verdict

    def _format_search_results(self, results: list[dict[str, Any]]) -> str:
        """Format search results for LLM consumption.

        Args:
            results: List of search result dicts

        Returns:
            Formatted string for prompt
        """
        if not results:
            return "No search results available."

        formatted = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "Unknown")
            url = result.get("url", "")
            content = result.get("content", result.get("snippet", ""))
            formatted.append(f"{i}. {title}\n   URL: {url}\n   Content: {content}")

        return "\n\n".join(formatted)

    def _parse_verdict_response(self, response_text: str) -> dict[str, Any]:
        """Parse LLM response JSON into verdict fields.

        Args:
            response_text: Raw LLM response (should be JSON)

        Returns:
            Dict with verdict, note, source_url, source_title, source_date
        """
        try:
            # Extract JSON from response (may have surrounding text)
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx == -1 or end_idx == 0:
                raise ValueError(f"No JSON found in response: {response_text}")

            json_str = response_text[start_idx:end_idx]
            data = json.loads(json_str)

            # Validate required fields
            required = ["verdict", "note"]
            for field in required:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            return {
                "verdict": data["verdict"],
                "note": data["note"],
                "source_url": data.get("source_url"),
                "source_title": data.get("source_title"),
                "source_date": data.get("source_date"),
            }
        except Exception as e:
            logger.error(f"Failed to parse verdict response: {str(e)}")
            # Return safe default
            return {
                "verdict": "Unverified",
                "note": "Could not parse LLM response",
                "source_url": None,
                "source_title": None,
                "source_date": None,
            }

    def extract_claims_from_summary(self, summary: dict) -> list[ClaimModel]:
        """Extract and validate claims from summary JSON.

        Args:
            summary: Summary dict with 'claims' key

        Returns:
            List of validated ClaimModel objects

        Raises:
            ValueError: If claims cannot be extracted or validated
        """
        if "claims" not in summary:
            raise ValueError("Summary missing 'claims' key")

        claims_data = summary["claims"]
        if not isinstance(claims_data, list):
            raise ValueError(f"Expected 'claims' to be a list, got {type(claims_data)}")

        claims = []
        for claim_data in claims_data:
            try:
                claim = ClaimModel(**claim_data)
                claims.append(claim)
            except Exception as e:
                logger.warning(f"Invalid claim data: {str(e)}")
                # Skip invalid claims, continue with others
                continue

        if not claims:
            raise ValueError("No valid claims extracted from summary")

        logger.info(f"Extracted {len(claims)} claims from summary")
        return claims

    def build_report(
        self, video_id: str, summary: dict, verdicts: list[VerdictModel]
    ) -> dict[str, Any]:
        """Construct report dictionary from video, summary, and verdicts.

        Args:
            video_id: Video identifier
            summary: Summary dict with metadata
            verdicts: List of VerdictModel objects

        Returns:
            Dict ready for ReportModel validation
        """
        # Calculate verdict breakdown
        verdict_breakdown = {
            "True": 0,
            "Partially supported/overstated": 0,
            "Unverified": 0,
            "False": 0,
        }
        for verdict in verdicts:
            verdict_breakdown[verdict.verdict] += 1

        # Calculate total cost (sum of verdict costs)
        total_cost_usd = sum(v.reasoning_cost.get("cost_usd", 0.0) for v in verdicts)

        report_data = {
            "video_id": video_id,
            "title": summary.get("title", "Unknown"),
            "channel_name": summary.get("channel_name", "Unknown"),
            "channel_url": summary.get("channel_url", ""),
            "source_url": summary.get("source_url", ""),
            "transcript_source": summary.get("transcript_source", "Unknown"),
            "fact_checked_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "fact_check_duration_seconds": 0.1,  # Placeholder; will be set by caller
            "search_provider": "Tavily",
            "llm_model": self.config.llm_model,
            "cost": {
                "search_usd": 0.0,  # Would be populated by caller
                "llm_usd": total_cost_usd,
                "total_usd": total_cost_usd,
            },
            "summary": summary,
            "verdicts": [v.model_dump() for v in verdicts],
            "claim_count": len(summary.get("claims", [])),
            "verdict_count": len(verdicts),
            "verdict_breakdown": verdict_breakdown,
            "disclaimer": "FinFolio reports facts and their accuracy. This is not financial advice.",
        }

        logger.info(f"Report built for video {video_id} with {len(verdicts)} verdicts")
        return report_data

    def run_fact_check_single_video(self, video_id: str) -> None:
        """Main entry point: Fact-check a single video end-to-end.

        Orchestrates the full pipeline:
        1. Check if report already exists (idempotent)
        2. Load summary from storage
        3. Extract claims from summary
        4. For each claim: search + assign verdict
        5. Build report
        6. Validate report against schema
        7. Save report via storage
        8. Log results

        Args:
            video_id: Video identifier

        Raises:
            ValueError: If summary cannot be loaded or claims invalid
            Exception: On critical errors (API keys, storage issues)
        """
        start_time = time.time()
        verdicts = []
        summary = None
        claims = []

        try:
            logger.info(f"Starting fact-check for video: {video_id}")

            # Load summary from storage
            from finfolio.storage import has_report, load_summary, save_report

            logger.info(f"Loading summary for {video_id}")
            summary = load_summary(video_id)
            if summary is None:
                # If summary not found but report exists, assume idempotency
                if has_report(video_id):
                    logger.info(f"Report already exists for {video_id}, skipping (idempotent)")
                    return
                raise ValueError(f"Summary not found for video {video_id}")
            logger.info(f"Summary loaded for {video_id}")

            # Extract claims from summary
            logger.info(f"Extracting claims from summary for {video_id}")
            claims = self.extract_claims_from_summary(summary)
            logger.info(f"Extracted {len(claims)} claims for {video_id}")

            # Load existing report to support resumability
            import json as json_lib

            from finfolio import storage

            completed_ids = set()
            verdicts = []

            try:
                existing_report_path = storage.REPORTS_DIR / f"{video_id}.json"
                if existing_report_path.exists():
                    existing_report = json_lib.loads(existing_report_path.read_text())
                    completed_ids = extract_completed_claim_ids(existing_report)
                    verdicts = existing_report.get("verdicts", [])
                    claim_count = len(claims)

                    logger.info(
                        f"Resuming video {video_id}: {len(completed_ids)} of {claim_count} claims already verified",
                        extra={"video_id": video_id, "completed_count": len(completed_ids), "total_count": claim_count},
                    )
            except Exception as e:
                logger.warning(f"Could not load existing report for {video_id}: {str(e)}")
                verdicts = []
                completed_ids = set()

            # Fact-check each claim
            skipped_claims = []
            newly_verified = 0

            for i, claim in enumerate(claims, 1):
                # Skip if already verified
                if claim.id in completed_ids:
                    logger.info(
                        f"[{i}/{len(claims)}] Skipping verified claim: {claim.id}",
                        extra={"claim_id": claim.id, "reason": "already_verified"},
                    )
                    continue

                logger.info(
                    f"[{i}/{len(claims)}] Fact-checking claim {claim.id}",
                    extra={"claim_id": claim.id, "claim_text": claim.text[:50]},
                )

                # Skip opinion/forecast claims
                if claim.is_opinion:
                    logger.info(
                        f"Skipping opinion claim: {claim.id}",
                        extra={"claim_id": claim.id, "reason": "is_opinion=True"},
                    )
                    skipped_claims.append(claim.id)
                    continue

                if claim.is_forecast:
                    logger.info(
                        f"Skipping forecast claim: {claim.id}",
                        extra={"claim_id": claim.id, "reason": "is_forecast=True"},
                    )
                    skipped_claims.append(claim.id)
                    continue

                # Search for claim
                logger.debug(f"Searching for claim: {claim.text}")
                search_results = self.search_client.search(claim.text)
                logger.info(
                    f"Search returned {len(search_results)} results for {claim.id}",
                    extra={"claim_id": claim.id, "result_count": len(search_results)},
                )

                # Fact-check claim
                verdict = self.fact_check_claim(claim, search_results)
                verdicts.append(verdict.model_dump())
                newly_verified += 1
                logger.info(
                    f"Verdict assigned for {claim.id}: {verdict.verdict}",
                    extra={
                        "claim_id": claim.id,
                        "verdict": verdict.verdict,
                        "source_url": verdict.source_url,
                    },
                )

            # Build report from VerdictModels
            duration_seconds = time.time() - start_time
            logger.info(f"Building final report for {video_id} with {len(verdicts)} verdicts")

            # Convert verdict dicts back to VerdictModels for build_report
            verdict_models = [VerdictModel(**v) for v in verdicts]
            report_data = self.build_report(video_id, summary, verdict_models)
            report_data["fact_check_duration_seconds"] = duration_seconds

            # Validate report schema
            try:
                ReportModel(**report_data)
                logger.info(
                    f"Report schema validated for {video_id}",
                    extra={
                        "video_id": video_id,
                        "verdict_count": len(verdicts),
                        "duration_seconds": duration_seconds,
                    },
                )
            except Exception as e:
                logger.error(f"Report validation failed for {video_id}: {str(e)}")
                raise

            # Save final report
            logger.info(f"Saving final report for {video_id}")
            save_report(video_id, report_data)
            logger.info(
                f"Report saved successfully for {video_id}",
                extra={
                    "video_id": video_id,
                    "claim_count": len(claims),
                    "verdict_count": len(verdicts),
                    "newly_verified": newly_verified,
                    "completed_previously": len(completed_ids),
                    "skipped_count": len(skipped_claims),
                    "duration_seconds": round(duration_seconds, 2),
                    "cost_usd": report_data["cost"]["total_usd"],
                },
            )

        except Exception as e:
            logger.error(
                f"Fact-checking failed for {video_id}: {str(e)}",
                extra={"video_id": video_id, "error": str(e)},
                exc_info=True,
            )
            # Save partial report if we have any verdicts
            if verdicts:
                try:
                    duration_seconds = time.time() - start_time
                    verdict_models = [VerdictModel(**v) for v in verdicts]
                    report_data = self.build_report(video_id, summary, verdict_models)
                    report_data["fact_check_duration_seconds"] = duration_seconds
                    save_report(video_id, report_data)
                    logger.info(
                        f"Partial report saved for {video_id} with {len(verdicts)} verdicts",
                        extra={"video_id": video_id, "verdict_count": len(verdicts)},
                    )
                except Exception as save_error:
                    logger.error(
                        f"Failed to save partial report for {video_id}: {str(save_error)}"
                    )
            raise


def extract_completed_claim_ids(report: dict | None) -> set[str]:
    """Extract set of completed claim IDs from existing report.

    Enables resumability: on retry, skip claims that were already verified.

    Args:
        report: Report dict or None if no report exists

    Returns:
        Set of claim IDs that have verdicts (empty set if no report)
    """
    if report is None:
        return set()

    verdicts = report.get("verdicts", [])
    return {v.get("claim_id") for v in verdicts if v.get("claim_id")}


def extract_claims_from_summary(summary: dict) -> list[ClaimModel]:
    """Standalone function to extract claims from summary.

    Args:
        summary: Summary dict with 'claims' key

    Returns:
        List of validated ClaimModel objects

    Raises:
        ValueError: If claims cannot be extracted
    """
    if "claims" not in summary:
        raise ValueError("Summary missing 'claims' key")

    claims_data = summary["claims"]
    if not isinstance(claims_data, list):
        raise ValueError(f"Expected 'claims' to be a list, got {type(claims_data)}")

    claims = []
    for claim_data in claims_data:
        try:
            claim = ClaimModel(**claim_data)
            claims.append(claim)
        except Exception as e:
            logger.warning(f"Invalid claim data: {str(e)}")
            continue

    if not claims:
        raise ValueError("No valid claims extracted from summary")

    logger.info(f"Extracted {len(claims)} claims from summary")
    return claims
