from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from repodoctor.app import run
from repodoctor.config import ConfigError, RepoDoctorConfig

app = typer.Typer(
    help="Check repository health, structure, and security hygiene.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Run repository health checks."""


@app.command()
def check(
    target: Annotated[
        Path | None,
        typer.Argument(help="Repository directory to check."),
    ] = None,
) -> None:
    """Validate a repository target for analysis."""
    try:
        config = RepoDoctorConfig.from_target(target)
    except ConfigError as error:
        typer.echo(f"Error: {error}")
        raise typer.Exit(code=2) from error

    result = run(config)
    message = Text("Foundation ready: ", style="green")
    message.append(str(result.target))
    Console().print(message, soft_wrap=True)
