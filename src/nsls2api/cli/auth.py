import configparser
import getpass
import os
from configparser import NoOptionError, NoSectionError
from pathlib import Path
from typing import Optional

import httpx
import typer

from nsls2api.infrastructure.security import SpecialUsers

BASE_URL = "http://localhost:8000"

app = typer.Typer()


def config_from_file() -> Optional[str]:
    config = configparser.ConfigParser()
    config_userhome = os.path.expanduser("~")
    config_filepath = Path(config_userhome) / ".config" / "nsls2"
    print(f"Reading config from {config_filepath}")

    try:
        config.read(config_filepath)
        api_client_token = config.get("api", "token")
    except (NoSectionError, NoOptionError):
        # If there is no config we are just going to login as Anonymous
        # so no need to raise an error.
        return None

    return api_client_token


@app.command()
def status():
    # Let's see if there is a token in the local config file ?
    token = config_from_file()
    if token is None:
        print("No API token found")
        token = getpass.getpass(prompt="Please enter your API token:")
        if len(token) == 0:
            logged_in_username: SpecialUsers = SpecialUsers.anonymous
            print("Authenticated as anonymous")
            return

    # Let's test this token
    url = f"{BASE_URL}/v1/person/me"
    try:
        with httpx.Client() as client:
            headers = {"Authorization": f"{token}"}
            response = client.get(url, headers=headers)
            response.raise_for_status()
            logged_in_username = response.json()
    except httpx.RequestError as exc:
        print(f"An error occurred while trying to login {exc}")
        raise

    print(f"Authenticated as {logged_in_username}")
