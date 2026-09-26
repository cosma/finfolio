"""CLI entry point for FinFolio: Fetch, Summarize, and Fact-Check."""

import json
import os
import random
import sys
import time
from datetime import UTC, datetime

import click

from finfolio import storage
from finfolio.channel_monitor import ChannelMonitor
from finfolio.config import Config, load_api_key, load_config
from finfolio.fact_checker import FactChecker
from finfolio.logging_utils import configure_logging
from finfolio.storage import list_pending_videos, load_summary
from finfolio.transcript_fetcher import TranscriptFetcher
from finfolio.youtube_client import YouTubeClient


def _log_event(event: str, status: str, **kwargs) -> None:
    """Log CLI event as JSON."""
    log_entry = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "event": event,
        "status": status,
        **kwargs,
    }
    print(json.dumps(log_entry, default=str))
    sys.stdout.flush()


@click.group()
@click.option("--config", default="./channels.yaml", help="Path to channels.yaml config file")
@click.pass_context
def cli(ctx: click.Context, config: str) -> None:
    """FinFolio: Fact-checking system for finance content."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config


@cli.command()
@click.option(
    "--min-delay",
    default=10,
    type=float,
    help="Minimum delay in seconds between transcript fetches (default: 10)",
)
@click.option(
    "--max-delay",
    default=20,
    type=float,
    help="Maximum delay in seconds between transcript fetches (default: 20)",
)
@click.pass_context
def fetch(ctx: click.Context, min_delay: float, max_delay: float) -> None:
    """Check configured channels for new videos and fetch transcripts."""
    config_path = ctx.obj["config_path"]

    try:
        _log_event("fetch_start", "success")

        # Load API key
        try:
            api_key = load_api_key()
        except ValueError as e:
            _log_event("fetch_failed", "failed", error=str(e))
            sys.exit(1)

        # Load configuration
        try:
            channels = load_config(config_path)
            if not channels:
                _log_event("fetch_failed", "failed", error="NO_CHANNELS_CONFIGURED")
                sys.exit(1)
        except (FileNotFoundError, ValueError) as e:
            _log_event("fetch_failed", "failed", error=str(e))
            sys.exit(1)

        # Acquire lock
        if not storage.acquire_lock():
            _log_event("fetch_failed", "failed", error="ANOTHER_FETCH_RUNNING")
            sys.exit(2)

        try:
            # Initialize clients with API key
            youtube_client = YouTubeClient(api_key)
            channel_monitor = ChannelMonitor(youtube_client)
            transcript_fetcher = TranscriptFetcher(youtube_client, storage)

            # Clean up leftover .tmp files
            storage.cleanup_tmp_files()

            total_quota_used = 0
            processed_channels = 0
            total_new_videos = 0
            total_transcripts_saved = 0

            # Process each channel
            for channel in channels:
                channel_id = channel.get("channel_id")
                display_name = channel.get("display_name", channel_id)

                if not channel_id:
                    _log_event("fetch_channel", "failed", error="MISSING_CHANNEL_ID")
                    continue

                try:
                    # Get last fetch timestamp
                    last_fetch = storage.get_channel_last_fetch(channel_id)

                    # Check for new videos
                    new_videos = channel_monitor.check_channel(channel_id, display_name, last_fetch)
                    processed_channels += 1
                    total_new_videos += len(new_videos)

                    _log_event(
                        "fetch_channel",
                        "success",
                        channel_id=channel_id,
                        display_name=display_name,
                        new_videos=len(new_videos),
                    )

                    # Fetch transcripts for new videos
                    for i, video in enumerate(new_videos):
                        video_id = video.get("video_id")
                        if not video_id:
                            continue

                        # Save video metadata for easy reference
                        storage.save_video_metadata(
                            video_id=video_id,
                            title=video.get("title", "Unknown"),
                            channel_id=channel_id,
                            published_at=video.get("published_at", ""),
                        )

                        if transcript_fetcher.has_transcript(video_id):
                            _log_event(
                                "download_transcript",
                                "skipped",
                                video_id=video_id,
                                reason="already_exists",
                            )
                        else:
                            try:
                                if transcript_fetcher.fetch_and_save(video_id):
                                    total_transcripts_saved += 1
                                    _log_event("download_transcript", "success", video_id=video_id)
                                else:
                                    _log_event(
                                        "download_transcript",
                                        "failed",
                                        video_id=video_id,
                                        reason="no_captions",
                                    )
                            except Exception as e:
                                error_str = str(e)
                                _log_event(
                                    "download_transcript",
                                    "failed",
                                    video_id=video_id,
                                    error=error_str,
                                )

                                # Check if YouTube has blocked our IP (various error messages)
                                if (
                                    "too many requests" in error_str.lower()
                                    or "blocked" in error_str.lower()
                                ):
                                    _log_event(
                                        "fetch_failed",
                                        "failed",
                                        error="IP_BLOCKED_BY_YOUTUBE",
                                        message="YouTube blocked your IP. Please wait and try again later.",
                                    )
                                    storage.release_lock()
                                    sys.exit(1)

                        # Add random delay between requests to avoid IP blocking
                        # Random delays mimic human behavior and prevent IP blocks
                        if i < len(new_videos) - 1:
                            random_delay = random.uniform(min_delay, max_delay)
                            time.sleep(random_delay)

                    # Update last fetch timestamp
                    storage.update_channel_last_fetch(channel_id, datetime.now(UTC))

                except Exception as e:
                    _log_event("fetch_channel", "failed", channel_id=channel_id, error=str(e))
                    continue

            # Get quota usage
            quota_usage = youtube_client.get_quota_units_used()
            total_quota_used = sum(quota_usage.values())

            # Final report
            _log_event(
                "fetch_complete",
                "success",
                channels_processed=processed_channels,
                new_videos_found=total_new_videos,
                transcripts_saved=total_transcripts_saved,
                quota_units=total_quota_used,
                quota_breakdown=quota_usage,
            )

            sys.exit(0)

        finally:
            # Always release lock
            storage.release_lock()

    except Exception as e:
        _log_event("fetch_failed", "failed", error=str(e))
        sys.exit(1)


@cli.command()
@click.option("--batch-size", default=100, type=int, help="Maximum transcripts to process per run")
@click.pass_context
def summarize(ctx: click.Context, batch_size: int) -> None:
    """Summarize all unsummarized transcripts using Claude."""
    try:
        from finfolio.summarizer import (
            InvalidOutputError,
            LLMAPIError,
            TranscriptTooLongError,
            TranscriptTooShortError,
            process_transcript_safe,
        )

        # Verify API credentials
        if not os.getenv("ANTHROPIC_API_KEY"):
            _log_event("summarization_failed", "failed", error="ANTHROPIC_API_KEY not set")
            sys.exit(1)

        _log_event("summarization_start", "success")

        # Get transcripts directory
        transcripts_dir = storage.TRANSCRIPTS_DIR
        if not transcripts_dir.exists():
            _log_event(
                "summarization_failed", "failed", error="Transcripts directory does not exist"
            )
            sys.exit(1)

        # Find all unsummarized transcripts
        transcript_files = sorted(transcripts_dir.glob("*.txt"))
        processed_count = 0
        error_count = 0
        skipped_count = 0
        total_cost_usd = 0.0

        for _i, transcript_file in enumerate(transcript_files[:batch_size]):
            video_id = transcript_file.stem
            try:
                transcript_text = transcript_file.read_text(encoding="utf-8")
                result = process_transcript_safe(video_id, transcript_text)

                if result is None:
                    # Already summarized, skipped
                    skipped_count += 1
                else:
                    processed_count += 1
                    cost = result.metadata.cost_usd or 0.0
                    total_cost_usd += cost
                    _log_event(
                        "transcript_processed",
                        "success",
                        video_id=video_id,
                        claims_count=len(result.claims),
                        cost_usd=round(cost, 6),
                    )

            except TranscriptTooShortError as e:
                error_count += 1
                _log_event(
                    "transcript_error",
                    "failed",
                    video_id=video_id,
                    error=f"Transcript validation: {str(e)}",
                )
            except TranscriptTooLongError as e:
                error_count += 1
                _log_event(
                    "transcript_error",
                    "failed",
                    video_id=video_id,
                    error=f"Transcript too long: {str(e)}",
                )
            except LLMAPIError as e:
                error_msg = str(e)
                _log_event(
                    "transcript_error",
                    "failed",
                    video_id=video_id,
                    error_type="LLMAPIError",
                    error_details=error_msg,
                )
                _log_event(
                    "summarization_failed",
                    "failed",
                    reason="LLM API failure",
                    video_id=video_id,
                    details=error_msg,
                )
                sys.exit(1)
            except InvalidOutputError as e:
                error_msg = str(e)
                _log_event(
                    "transcript_error",
                    "failed",
                    video_id=video_id,
                    error_type="InvalidOutputError",
                    error_details=error_msg,
                )
                _log_event(
                    "summarization_failed",
                    "failed",
                    reason="Invalid LLM output",
                    video_id=video_id,
                    details=error_msg,
                )
                sys.exit(1)
            except Exception as e:
                error_msg = str(e)
                _log_event(
                    "transcript_error",
                    "failed",
                    video_id=video_id,
                    error_type=type(e).__name__,
                    error_details=error_msg,
                )
                _log_event(
                    "summarization_failed",
                    "failed",
                    reason="Unexpected error",
                    video_id=video_id,
                    details=error_msg,
                )
                sys.exit(1)

        # Final report
        _log_event(
            "summarization_complete",
            "success" if error_count == 0 else "partial",
            processed=processed_count,
            errors=error_count,
            skipped=skipped_count,
            total_cost_usd=round(total_cost_usd, 6),
        )

        # Exit with appropriate code
        if error_count > 0 and processed_count == 0:
            sys.exit(1)  # All failed
        sys.exit(0)  # At least some succeeded

    except Exception as e:
        _log_event("summarization_failed", "failed", error=str(e))
        sys.exit(1)


@cli.command()
@click.option(
    "--limit", type=int, default=None, help="Process at most N videos (default: all pending)"
)
@click.option(
    "--video-id",
    type=str,
    default=None,
    help="Process a single video by ID (overrides --limit)",
)
@click.option("--verbose", is_flag=True, help="Enable DEBUG logging")
def factcheck(
    limit: int | None, video_id: str | None, verbose: bool
) -> None:
    """Fact-check extracted claims from video summaries."""
    log_level = "DEBUG" if verbose else "INFO"
    logger = configure_logging(log_level)

    try:
        # Load and validate config
        config = Config()
        config.validate()

        # Initialize fact checker
        checker = FactChecker(config)

        # Determine which videos to process
        if video_id:
            # Single video mode
            video_ids = [video_id]
            click.echo(f"Processing single video: {video_id}")
        else:
            # Batch mode
            video_ids = list_pending_videos()
            if limit:
                video_ids = video_ids[:limit]

            if not video_ids:
                click.echo("No pending videos to process.")
                return

            click.echo(f"Processing {len(video_ids)} pending videos...")

        # Process videos
        start_time = time.time()
        videos_processed = 0
        claims_verified = 0
        errors_total = 0

        for i, vid_id in enumerate(video_ids, 1):
            try:
                click.echo(f"[{i}/{len(video_ids)}] {vid_id}: ", nl=False)

                # Fact-check video
                checker.run_fact_check_single_video(vid_id)

                # Get report info (would need to read from storage)
                summary = load_summary(vid_id)
                if summary:
                    claim_count = len(summary.get("claims", []))
                    click.echo(f"✓ {claim_count} claims processed")
                    videos_processed += 1
                    claims_verified += claim_count
                else:
                    click.echo("✓ processed")
                    videos_processed += 1

            except Exception as e:
                logger.error(f"Error processing {vid_id}: {str(e)}", exc_info=True)
                click.echo(f"✗ error: {str(e)[:50]}")
                errors_total += 1

        # Print summary
        duration = time.time() - start_time
        click.echo("\n" + "=" * 60)
        click.echo("Summary:")
        click.echo(f"  Videos processed: {videos_processed}")
        click.echo(f"  Claims verified: {claims_verified}")
        click.echo(f"  Errors: {errors_total}")
        click.echo(f"  Duration: {duration:.1f}s")
        click.echo("=" * 60)

        sys.exit(0 if errors_total == 0 or videos_processed > 0 else 1)

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        click.echo(f"ERROR: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        click.echo(f"ERROR: {str(e)}", err=True)
        sys.exit(1)


class _MainWrapper:
    """Hybrid main entry point supporting both Click and direct call interfaces.

    - For Click CliRunner: acts as the Click group (has .name, supports invoke, etc)
    - For direct calls with patched sys.argv: returns an exit code
    """

    def __init__(self, click_group):
        self._click_group = click_group
        # Copy Click group attributes for CliRunner compatibility
        self.name = click_group.name
        self.callback = click_group.callback
        self.params = click_group.params
        self.help = click_group.help

    def __call__(self, *args, **kwargs):
        """Support both direct calls and Click invocation."""
        try:
            # Call the Click group
            self._click_group(*args, **kwargs)
            return 0
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else (1 if e.code else 0)

    def __getattr__(self, name):
        """Proxy other attributes to the Click group."""
        return getattr(self._click_group, name)


main = _MainWrapper(cli)


if __name__ == "__main__":
    sys.exit(main())
