from typing import Optional

import typer

from nsls2api.cli import admin, api, auth, beamline, facility, proposal

__app_name__ = "nsls2api-cli"
__version__ = "0.1.0"

app = typer.Typer()
app.add_typer(admin.app, name="admin", help="Do powerful admin level magic")
app.add_typer(api.app, name="api", help="Make NSLS-II API request")
app.add_typer(auth.app, name="auth", help="Stuff about security and fun")
app.add_typer(beamline.app, name="beamline", help="Stuff about Beamlines")
app.add_typer(facility.app, name="facility", help="Stuff about Facilities")
app.add_typer(proposal.app, name="proposal", help="Stuff about Proposals")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__app_name__} v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the application's version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    return
