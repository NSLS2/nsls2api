from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from nsls2api.infrastructure.config import get_settings
from nsls2api.infrastructure.logging import logger
from nsls2api.models.slack_models import SlackBot

settings = get_settings()

# def get_super_app() -> App:
#     return App(
#     token=settings.superadmin_slack_user_token,
#     signing_secret=settings.slack_signing_secret,
# )

def get_boring_app() -> App:
    return App(
        token=settings.slack_bot_token,
        signing_secret=settings.slack_signing_secret,
    )

def get_bot_details() -> SlackBot:
    """
    Retrieves the details of the Slack bot.

    Returns:
        SlackBot: An instance of the SlackBot class containing the bot details.
    """
    response = get_boring_app().client.auth_test()

    return SlackBot(
        username=response.data["user"],
        user_id=response.data["user_id"],
        bot_id=response.data["bot_id"],
    )


def get_channel_members(channel_id: str) -> list[str]:
    """
    Retrieves the members of a Slack channel.
    It assumes that the bot is already a member of the
    channel (if it is a private channel)

    Args:
        channel_id (str): The ID of the Slack channel.

    Returns:
        list[str]: A list of member IDs in the channel.
    """
    try:
        response = get_boring_app().client.conversations_members(channel=channel_id)
    except SlackApiError as error:
        logger.exception(error)
        return []
    return response.data["members"]


def add_bot_to_channel(channel_id: str):
    """
    Adds the bot to the specified channel.

    Args:
        channel_id (str): The ID of the channel to add the bot to.

    Raises:
        Exception: If an error occurs while adding the bot to the channel.

    Returns:
        None
    """
    bot = get_bot_details()
    client = WebClient(token=settings.superadmin_slack_user_token)
    logger.info(f"Inviting {bot.username} ({bot.user_id}) to channel {channel_id}.")
    try:
        response = client.admin_conversations_invite(
            channel_id=channel_id, user_ids=[bot.user_id]
        )
        logger.info(response)
    except SlackApiError as error:
        if error.response["error"] == "failed_for_some_users":
            channel_members = get_channel_members(channel_id)
            if "failed_user_ids" in error.response:
                if (bot.user_id in error.response["failed_user_ids"]) and (
                    bot.user_id in channel_members
                ):
                    logger.info(f"{bot.username} is already in channel {channel_id}.")
                else:
                    logger.error(
                        f"Failed to add bot {bot.username} to channel {channel_id}."
                    )
        else:
            logger.exception(error)
            raise Exception(error) from error


async def is_channel_private(channel_id: str) -> bool:
    """
    Checks if a Slack channel is private.

    Args:
        channel_id (str): The ID of the channel to check.

    Returns:
        bool: True if the channel is private, False otherwise.
    """
    response = get_boring_app().client.conversations_info(channel=channel_id)
    return response.data["channel"]["is_private"]


async def create_channel(
    name: str,
    is_private: bool = True,
) -> str | None:
    """
    Creates a new Slack channel with the given name and privacy settings.  If the channel 
    already exists, it will convert the channel to the desired privacy setting and invite 
    the necessary bot user to the channel.

    Args:
        name (str): The name of the channel to be created.
        is_private (bool, optional): Whether the channel should be private. Defaults to True.

    Returns:
        str | None: The ID of the created channel if successful, None otherwise.
    """
    super_client = WebClient(token=settings.superadmin_slack_user_token)

    # Does the channel already exist?
    channel_id = channel_id_from_name(name)

    if channel_id:
        logger.info(f"Found existing channel called {name}.")
        if is_private:
            if await is_channel_private(channel_id):
                logger.info("Channel is already private.")
            else:
                try:
                    logger.info(f"Trying to convert channel {name} to private.")
                    response = super_client.admin_conversations_convertToPrivate(
                        channel_id=channel_id
                    )
                    logger.info(
                        f"Response from converting channel to private: {response}"
                    )
                except SlackApiError as e:
                    logger.exception(f"Error converting channel to private: {e}")
                    return None
        else:
            if await is_channel_private(channel_id):
                try:
                    logger.info(f"Trying to convert channel {name} to public.")
                    response = super_client.admin_conversations_convertToPublic(
                        channel_id=channel_id
                    )
                    logger.info(
                        f"Response from converting channel to public: {response}"
                    )
                except SlackApiError as e:
                    logger.exception(f"Error converting channel to public: {e}")
                    return None

    else:
        try:
            logger.info(f"Trying to create channel called '{name}'.")
            response = super_client.admin_conversations_create(
                name=name,
                is_private=is_private,
                team_id=settings.nsls2_workspace_team_id,
            )
            logger.info(f"Response from creating slack channel: {response}")

        except SlackApiError as e:
            logger.exception(f"Error creating channel: {e}")
            return None

    # Now lets add our 'bot' to the channel
    add_bot_to_channel(channel_id)

    return channel_id


def channel_id_from_name(name: str) -> str | None:
    """
    Retrieves the channel ID for a given channel name.

    Args:
        name (str): The name of the channel.

    Returns:
        str | None: The ID of the channel if found, None otherwise.
    """
    client = WebClient(token=settings.superadmin_slack_user_token)
    response = client.admin_conversations_search(query=name)
    # This returns a list of channels, find the one with the exact name (just in case we get more than one returned)
    for channel in response["conversations"]:
        if channel["name"] == name:
            return channel["id"]


def rename_channel(name: str, new_name: str) -> str | None:
    """
    Renames a Slack channel.

    Args:
        name (str): The current name of the channel.
        new_name (str): The new name for the channel.

    Returns:
        str | None: The ID of the renamed channel, or None if the channel was not found.

    Raises:
        Exception: If the channel with the given name is not found.
        Exception: If the channel renaming fails.
    """
    channel_id = channel_id_from_name(name)
    if channel_id is None:
        raise Exception(f"Channel {name} not found.")

    response = get_boring_app().client.conversations_rename(channel=channel_id, name=new_name)

    if response.data["ok"] is not True:
        raise Exception(f"Failed to rename channel {name} to {new_name}")

    if channel_id is None:
        return None

    return channel_id


def lookup_userid_by_email(email: str) -> str | None:
    """
    Looks up the user ID associated with the given email address.

    Args:
        email (str): The email address of the user.

    Returns:
        str | None: The user ID if found, None otherwise.
    """
    response = get_boring_app().client.users_lookupByEmail(email=email)
    if response.data["ok"] is True:
        return response.data["user"]["id"]


def lookup_username_by_email(email: str) -> str | None:
    """
    Looks up the username associated with the given email address.

    Args:
        email (str): The email address to look up.

    Returns:
        str | None: The username associated with the email address, or None if not found.
    """
    response = get_boring_app().client.users_lookupByEmail(email=email)
    if response.data["ok"] is True:
        return response.data["user"]["name"]


def add_users_to_channel(channel_id: str, user_ids: list[str]):
    try:
        userlist = ",".join(user_ids)
        app.client.conversations_invite(channel=channel_id, users=userlist)
    except SlackApiError as error:
        if error.response["error"] == "failed_for_some_users":
            channel_members = get_channel_members(channel_id)
            if "failed_user_ids" in error.response:
                for failed_user_id in error.response["failed_user_ids"]:
                    if failed_user_id in channel_members:
                        logger.info(
                            f"{failed_user_id} is already in channel {channel_id}."
                        )
                    else:
                        logger.error(
                            f"Failed to add user {failed_user_id} to channel {channel_id}."
                        )
        else:
            logger.exception(error)
            raise Exception(error) from error
