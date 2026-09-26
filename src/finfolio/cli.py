"""CLI command for fact-checking: finfolio factcheck."""

import argparse
import logging
import sys
import time

from finfolio.config import Config
from finfolio.fact_checker import FactChecker
from finfolio.logging_utils import configure_logging
from finfolio.storage import list_pending_videos


def main() -> int:
    """Main CLI entry point for fact-checking.

    Returns:
        Exit code (0 = success, 1 = fatal error, 2 = argument error)
    """
    parser = argparse.ArgumentParser(
        prog="finfolio", description="Fact-checking system for finance content"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Fact-check command
    factcheck_parser = subparsers.add_parser(
        "factcheck", help="Fact-check extracted claims from video summaries"
    )
    factcheck_parser.add_argument(
        "--limit", type=int, default=None, help="Process at most N videos (default: all pending)"
    )
    factcheck_parser.add_argument(
        "--video-id",
        type=str,
        default=None,
        help="Process a single video by ID (overrides --limit)",
    )
    factcheck_parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging")

    args = parser.parse_args()

    # Default to factcheck if no command specified
    if not args.command:
        args.command = "factcheck"
        args.limit = None
        args.video_id = None
        args.verbose = False

    # Configure logging
    log_level = "DEBUG" if getattr(args, "verbose", False) else "INFO"
    logger = configure_logging(log_level)

    try:
        # Load and validate config
        config = Config()
        config.validate()

        if args.command == "factcheck":
            return cmd_factcheck(config, logger, args)
        else:
            parser.print_help()
            return 2

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        print(f"ERROR: {str(e)}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"ERROR: {str(e)}", file=sys.stderr)
        return 1


def cmd_factcheck(config: Config, logger: logging.Logger, args) -> int:
    """Execute fact-checking command.

    Args:
        config: Configuration object
        logger: Logger instance
        args: Parsed arguments

    Returns:
        Exit code (0 = success, 1 = error)
    """
    try:
        # Initialize fact checker
        checker = FactChecker(config)

        # Determine which videos to process
        if args.video_id:
            # Single video mode
            video_ids = [args.video_id]
            print(f"Processing single video: {args.video_id}")
        else:
            # Batch mode
            video_ids = list_pending_videos()
            if args.limit:
                video_ids = video_ids[: args.limit]

            if not video_ids:
                print("No pending videos to process.")
                return 0

            print(f"Processing {len(video_ids)} pending videos...")

        # Process videos
        start_time = time.time()
        videos_processed = 0
        claims_verified = 0
        errors_total = 0

        for i, video_id in enumerate(video_ids, 1):
            try:
                print(f"[{i}/{len(video_ids)}] {video_id}: ", end="", flush=True)

                # Fact-check video
                checker.run_fact_check_single_video(video_id)

                # Get report info (would need to read from storage)
                from finfolio.storage import load_summary

                summary = load_summary(video_id)
                if summary:
                    claim_count = len(summary.get("claims", []))
                    print(f"✓ {claim_count} claims processed")
                    videos_processed += 1
                    claims_verified += claim_count
                else:
                    print("✓ processed")
                    videos_processed += 1

            except Exception as e:
                logger.error(f"Error processing {video_id}: {str(e)}", exc_info=True)
                print(f"✗ error: {str(e)[:50]}")
                errors_total += 1

        # Print summary
        duration = time.time() - start_time
        print("\n" + "=" * 60)
        print("Summary:")
        print(f"  Videos processed: {videos_processed}")
        print(f"  Claims verified: {claims_verified}")
        print(f"  Errors: {errors_total}")
        print(f"  Duration: {duration:.1f}s")
        print("=" * 60)

        return 0 if errors_total == 0 or videos_processed > 0 else 1

    except Exception as e:
        logger.error(f"Fatal error in fact-checking: {str(e)}", exc_info=True)
        print(f"ERROR: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
