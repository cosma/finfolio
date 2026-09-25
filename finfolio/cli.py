"""CLI entry point for finfolio fetch command."""

import json
import os
import random
import sys
import time
from datetime import UTC, datetime

import click

from finfolio import storage
from finfolio.channel_monitor import ChannelMonitor
from finfolio.config import load_api_key, load_config
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
def main(ctx: click.Context, config: str) -> None:
    """FinFolio: Fact-checking system for finance content."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config


@main.command()
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


@main.command()
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


if __name__ == "__main__":
    main()
