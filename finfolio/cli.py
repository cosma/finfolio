"""CLI entry point for finfolio fetch command."""
import json
import sys
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
        **kwargs
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
@click.pass_context
def fetch(ctx: click.Context) -> None:
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
            # Initialize clients
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

                    _log_event("fetch_channel", "success", channel_id=channel_id,
                              display_name=display_name, new_videos=len(new_videos))

                    # Fetch transcripts for new videos
                    for video in new_videos:
                        video_id = video.get("video_id")
                        if not video_id:
                            continue

                        # Save video metadata for easy reference
                        storage.save_video_metadata(
                            video_id=video_id,
                            title=video.get("title", "Unknown"),
                            channel_id=channel_id,
                            published_at=video.get("published_at", "")
                        )

                        if transcript_fetcher.has_transcript(video_id):
                            _log_event("download_transcript", "skipped", video_id=video_id,
                                      reason="already_exists")
                        else:
                            try:
                                if transcript_fetcher.fetch_and_save(video_id):
                                    total_transcripts_saved += 1
                                    _log_event("download_transcript", "success", video_id=video_id)
                                else:
                                    _log_event("download_transcript", "failed", video_id=video_id,
                                              reason="no_captions")
                            except Exception as e:
                                _log_event("download_transcript", "failed", video_id=video_id,
                                          error=str(e))

                    # Update last fetch timestamp
                    storage.update_channel_last_fetch(channel_id, datetime.now(UTC))

                except Exception as e:
                    _log_event("fetch_channel", "failed", channel_id=channel_id,
                              error=str(e))
                    continue

            # Get quota usage
            quota_usage = youtube_client.get_quota_units_used()
            total_quota_used = sum(quota_usage.values())

            # Final report
            _log_event("fetch_complete", "success",
                      channels_processed=processed_channels,
                      new_videos_found=total_new_videos,
                      transcripts_saved=total_transcripts_saved,
                      quota_units=total_quota_used,
                      quota_breakdown=quota_usage)

            sys.exit(0)

        finally:
            # Always release lock
            storage.release_lock()

    except Exception as e:
        _log_event("fetch_failed", "failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
