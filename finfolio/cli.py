"""CLI entry point for finfolio fetch command."""
import click


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
    pass


if __name__ == "__main__":
    main()
