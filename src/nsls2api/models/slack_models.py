from datetime import datetime

import pydantic


class SlackUser(pydantic.BaseModel):
    user_id: str
    username: str
    real_name: str | None = None
    is_bot: bool = False
    pending_invitation: bool = False


class SlackUserProfile(pydantic.BaseModel):
    """
    Represents a Slack user's profile information.

    Attributes:
        display_name (str | None): The display name of the user.
        email (str | None): The email address of the user.
        first_name (str | None): The user's first name.
        last_name (str | None): The user's last name.
        status_emoji (str | None): The emoji set as the user's status such as :train:.
        status_text (str | None): The displayed status text of up to 100 characters.
        status_expiration (datetime | None): Unix timestamp of when the status will expire.
        team (str | None): The ID of the team the user is on.
        title (str | None): The user's title or role.
    """

    display_name: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    status_emoji: str | None = None
    status_text: str | None = pydantic.Field(default=None, max_length=100)
    status_expiration: datetime | None = None
    team: str | None = None
    title: str | None = None


class SlackPerson(SlackUser):
    email: str


class SlackBot(SlackUser):
    bot_id: str


class SlackChannel(pydantic.BaseModel):
    channel_id: str
    channel_name: str


class SlackChannelToCreate(pydantic.BaseModel):
    channel_name: str
    proposal_id: str
    beamlines: list[str] | None = None
    topic: str | None = None


class ProposalSlackChannel(SlackChannel):
    topic: str | None = None
    users: list[SlackUser] | None = None
    managers: list[SlackUser] | None = None
    bots: list[SlackBot] | None = None
    is_private: bool


class SlackChannelResponseModel(pydantic.BaseModel):
    channel_id: str
    channel_name: str
    beamline_slack_managers: list[str] | None = []
    user_ids: list[str] | None = []
    message: str | None = None


class ProposalSlackChannelList(pydantic.BaseModel):
    slack_channels: list[ProposalSlackChannel]
    count: int


class SlackConversation(pydantic.BaseModel):
    conversation_id: str
    name: str
    is_private: bool
    topic: str | None = None
    purpose: str | None = None
    creator: str | None = None
    is_archived: bool = False
    updated: datetime | None = None
    created: datetime | None = None
    num_members: int = 0
    members: list[SlackUser] | None = None
