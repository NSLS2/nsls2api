from typing import Annotated, Optional

import fastapi
from fastapi import Depends, HTTPException

from nsls2api.api.models.facility_model import FacilityName
from nsls2api.api.models.proposal_model import SingleProposal
from nsls2api.infrastructure import config
from nsls2api.infrastructure.logging import logger
from nsls2api.infrastructure.security import (
    generate_api_key,
    validate_admin_role,
)
from nsls2api.models.apikeys import (
    ApiUser,
    ApiUserResponseModel,
    ApiUserRole,
    ApiUserType,
)
from nsls2api.models.slack_models import SlackChannelCreationResponseModel
from nsls2api.services import beamline_service, proposal_service, slack_service

# router = fastapi.APIRouter()
router = fastapi.APIRouter(
    dependencies=[Depends(validate_admin_role)], include_in_schema=True, tags=["admin"],
)


@router.get("/admin/settings")
async def info(settings: Annotated[config.Settings, Depends(config.get_settings)]):
    return settings


@router.get("/admin/validate", response_model=str)
async def check_admin_validation(
    admin_user: Annotated[ApiUser, Depends(validate_admin_role)] = None,
):
    """:return: str - The username of the validated admin user.
    """
    if admin_user is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key",
        )

    return admin_user.username


@router.post("/admin/generate-api-key/{username}")
async def generate_user_apikey(username: str, usertype: ApiUserType = ApiUserType.user):
    """Generate an API key for a given username.

    :param username: The username for which to generate the API key.
    :param usertype: The type of API key to generate.
    :return: The generated API key.
    """
    return await generate_api_key(username, usertype=usertype)


@router.post("/admin/proposal/generate-test")
async def generate_fake_proposal(
    add_specific_user: str | None = None,
) -> Optional[SingleProposal]:
    proposal = await proposal_service.generate_fake_test_proposal(
        FacilityName.nsls2, add_specific_user,
    )

    if proposal is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate a fake test proposal",
        )

    return SingleProposal(proposal=proposal)


@router.post("/admin/slack/create-proposal-channel/{proposal_id}")
async def create_slack_channel(proposal_id: str) -> SlackChannelCreationResponseModel:
    proposal = await proposal_service.proposal_by_id(proposal_id)

    if proposal is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )

    channel_name = proposal_service.slack_channel_name_for_proposal(proposal_id)

    if channel_name is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Slack channel name could not be generated for the proposal {proposal_id}",
        )

    channel_id = await slack_service.create_channel(
        channel_name,
        is_private=True,
    )

    if channel_id is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Slack channel could not be created for the proposal {proposal_id}",
        )

    logger.info(f"Created slack channel '{channel_name}' for proposal {proposal_id}.")

    # Store the created Slack channel ID
    proposal.slack_channel_id = channel_id
    await proposal.save()

    # Add the beamline Slack channel managers to the channel
    slack_managers_added = []
    for beamline in proposal.instruments:
        slack_managers = await beamline_service.slack_channel_managers(beamline)
        logger.info(
            f"Adding Slack channel managers for {beamline} beamline [{slack_managers}].",
        )
        if len(slack_managers) > 0:
            slack_service.add_users_to_channel(
                channel_id=channel_id, user_ids=slack_managers,
            )
            slack_managers_added.append(slack_managers)

    # Add the users on the proposal to the channel
    proposal_user_ids = []
    for user in proposal.users:
        # If username is populated then user has an account
        if user.username is not None:
            user_slack_id = slack_service.lookup_userid_by_email(user.email)
            if user_slack_id is None:
                logger.info(f"User {user.username} does not have a slack_id")
            else:
                logger.info(
                    f"Adding user {user.username} ({user_slack_id}) to slack channel...",
                )
                proposal_user_ids.append(user_slack_id)

    logger.info(
        f"Slack users {proposal_user_ids} will be added to the proposal channel",
    )

    # TODO: Uncomment to actually add the users when we are sure!!
    # slack_service.add_users_to_channel(channel_id=channel_id, user_ids=proposal_user_ids)

    response_model = SlackChannelCreationResponseModel(
        channel_id=channel_id,
        channel_name=channel_name,
        beamline_slack_managers=slack_managers_added,
        user_ids=proposal_user_ids,
    )

    return response_model


@router.put("/admin/user/{username}/role/{role}")
async def update_user_role(username: str, role: ApiUserRole) -> ApiUserResponseModel:
    """Update the role of a user.

    :param username: The username of the user to update.
    :param role: The new role for the user.
    :return: The updated user object.
    """
    user = await ApiUser.find_one(ApiUser.username == username)
    if user is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"User {username} not found",
        )

    user.role = role
    await user.save()

    response = ApiUserResponseModel(
        id=user.id,
        username=user.username,
        type=user.type,
        role=user.role,
        created_on=user.created_on,
        last_updated=user.last_updated,
    )

    return response
