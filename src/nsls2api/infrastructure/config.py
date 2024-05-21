from functools import lru_cache
from pathlib import Path

from pydantic import MongoDsn, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Settings Class
    ==============

    This class represents the settings for the application. It inherits from the `BaseSettings` class provided by `pydantic_settings` library.

    Attributes:
    -----------
    pass_api_key (str): The API key used for authentication with the PASS API.
    pass_api_url (str): The URL of the PASS API. Defaults to "https://passservices.bnl.gov/passapi".
    active_directory_server (str): The server address for the Active Directory.
    active_directory_server_list (str): A list of Active Directory server addresses.
    n2sn_user_search (str): The search query for user information in N2SN.
    n2sn_group_search (str): The search query for group information in N2SN.
    bnlroot_ca_certs_file (str): The file path for the BNL root CA certificates.

    model_config (SettingsConfigDict): An instance of the `SettingsConfigDict` class, used for loading settings from an environment file (".env").

    Usage:
    ------
    settings = Settings()

    Example:
    --------
    settings = Settings()
    settings.pass_api_key = "123456"
    settings.active_directory_server = "ldap.example.com"
    settings.active_directory_server_list = "ldap1.example.com, ldap2.example.com"
    settings.n2sn_user_search = "user@example.com"
    settings.n2sn_group_search = "group@example.com"
    settings.bnlroot_ca_certs_file = "/path/to/ca_certs.pem"
    """

    pass_api_key: str
    pass_api_url: HttpUrl = "https://passservices.bnl.gov/passapi"
    active_directory_server: str
    active_directory_server_list: str
    n2sn_user_search: str
    n2sn_group_search: str
    bnlroot_ca_certs_file: str
    mongodb_dsn: MongoDsn
    # mongodb_dsn: MongoDsn = "mongodb://localhost:27017/nsls2core-test"

    use_socks_proxy: bool = False
    socks_proxy: str

    # Slack settings
    slack_bot_token: str | None = ""
    superadmin_slack_user_token: str | None = ""
    slack_signing_secret: str | None = ""
    nsls2_workspace_team_id: str | None = ""

    # Universal Proposal System
    universal_proposal_system_api_url: HttpUrl = "https://ups.servicenowservices.com/api"
    universal_proposal_system_api_user: str | None = ""
    universal_proposal_system_api_password : str | None = ""


    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"), extra='ignore',
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Retrieve the settings dictionary.

    :returns: The dictionary of current settings.
    """
    return Settings()