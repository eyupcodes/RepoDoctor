import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from repodoctor import __version__
from repodoctor.app import run
from repodoctor.config import ConfigError, RepoDoctorConfig
from repodoctor.report import render_report, result_to_dict

app = typer.Typer(
    help="Check repository health, structure, and security hygiene.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"repodoctor {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Run repository health checks."""


@app.command()
def check(
    target: Annotated[
        Path | None,
        typer.Argument(help="Repository directory to check."),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Print the result as one JSON object."),
    ] = False,
) -> None:
    """Validate a repository target for analysis."""
    try:
        config = RepoDoctorConfig.from_target(target)
    except ConfigError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error

    result = run(config)
    if as_json:
        typer.echo(json.dumps(result_to_dict(result), ensure_ascii=True))
    else:
        render_report(result, Console())
    if result.warnings or result.failures:
        raise typer.Exit(code=1)
