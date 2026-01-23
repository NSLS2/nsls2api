import fastapi
from fastapi import Depends, HTTPException, Request
from fastapi.security.api_key import APIKey

from nsls2api.api.models.proposal_model import (
    ProposalDirectoriesList,
)
from nsls2api.infrastructure.logging import logger
from nsls2api.infrastructure.security import (
    get_current_user,
    validate_admin_role,
)
from nsls2api.models.beamlines import (
    Beamline,
    BeamlineService,
    Detector,
    DetectorList,
    DirectoryList,
)
from nsls2api.services import beamline_service, slack_service

router = fastapi.APIRouter()


@router.get("/beamline/{name}", response_model=Beamline)
async def details(name: str):
    beamline = await beamline_service.beamline_by_name(name)
    if beamline is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Beamline '{name.upper()}' does not exist",
        )
    return beamline


@router.get("/beamline/{name}/service-accounts")
async def get_beamline_accounts(name: str, api_key: APIKey = Depends(get_current_user)):
    service_accounts = await beamline_service.service_accounts(name)
    if service_accounts is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Beamline '{name.upper()}' does not exist",
        )
    return service_accounts


@router.get("/beamline/{name}/slack-channel-managers")
async def get_beamline_slack_channel_managers(
    name: str, api_key: APIKey = Depends(get_current_user)
):
    slack_channel_managers = slack_service.verify_slack_users(
        await beamline_service.slack_channel_managers(name)
    )
    if slack_channel_managers is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Beamline '{name.upper()}' does not exist",
        )
    return slack_channel_managers


@router.get(
    "/beamline/{name}/detectors", response_model=DetectorList, include_in_schema=True
)
async def get_beamline_detectors(name: str) -> DetectorList:
    try:
        detectors = await beamline_service.detectors(name)
    except LookupError:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Beamline '{name.upper()}' does not exist",
        )
    response_model = DetectorList(detectors=detectors, count=len(detectors))
    return response_model


@router.put(
    "/beamline/{name}/detector/{detector_name}",
    include_in_schema=True,
    response_model=Detector,
    dependencies=[Depends(validate_admin_role)],
)
@router.delete(
    "/beamline/{name}/detector/{detector_name}",
    include_in_schema=True,
    response_model=Detector,
    dependencies=[Depends(validate_admin_role)],
)
async def add_or_delete_detector(
    request: Request, name: str, detector_name: str, detector: Detector | None = None
):
    if request.method == "PUT":
        logger.info(f"Adding detector {detector_name} to beamline {name.upper()}")

        if not detector:
            raise HTTPException(
                status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No detector information supplied in request body.",
            )
        if detector_name != detector.name:
            raise HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail=f"Detector name in path '{detector_name}' does not match name in body '{detector.name}'.",
            )

        new_detector = await beamline_service.add_detector(
            beamline_name=name,
            detector_name=detector.name,
            directory_name=detector.directory_name,
            granularity=detector.granularity,
            description=detector.description,
            manufacturer=detector.manufacturer,
        )

        if new_detector is None:
            raise HTTPException(
                status_code=fastapi.status.HTTP_409_CONFLICT,
                detail=f"Detector already exists in beamline {name.upper()} with either name '{detector.name}' or directory name '{detector.directory_name}'",
            )

        changed_detector = new_detector
    elif request.method == "DELETE":
        logger.info(f"Deleting detector {detector_name} from beamline {name.upper()}")

        deleted_detector = await beamline_service.delete_detector(
            beamline_name=name,
            detector_name=detector_name,
        )

        if deleted_detector is None:
            raise HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"Detector {detector_name} was not found for beamline {name.upper()}",
            )

        changed_detector = deleted_detector

    return changed_detector


@router.get(
    "/beamline/{name}/proposal-directory-skeleton",
    response_model=ProposalDirectoriesList,
    deprecated=True,
)
@router.get(
    "/beamline/{name}/directory-skeleton",
    response_model=DirectoryList,
)
async def get_beamline_directory_skeleton(name: str):
    directory_skeleton = await beamline_service.directory_skeleton(name)
    if directory_skeleton is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"No proposal directory skeleton for the {name.upper()} beamline could be generated.",
        )
    response_model = ProposalDirectoriesList(
        directory_count=len(directory_skeleton), directories=directory_skeleton
    )
    return response_model


# TODO: Review if we want to also have the following endpoints for the beamline accounts or
#       if we want to have a single endpoint (above) that returns all the accounts for a beamline.


@router.get(
    "/beamline/{name}/accounts/workflow", response_model=str, include_in_schema=False
)
async def get_beamline_workflow_username(name: str):
    workflow_user = await beamline_service.workflow_username(name)
    if workflow_user is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"No workflow user has been defined for the {name.upper()} beamline",
        )
    return workflow_user


@router.get(
    "/beamline/{name}/accounts/ioc", response_model=str, include_in_schema=False
)
async def get_beamline_ioc_username(name: str):
    ioc_user = await beamline_service.ioc_username(name)
    if ioc_user is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"No IOC user has been defined for the {name.upper()} beamline",
        )
    return ioc_user


@router.get(
    "/beamline/{name}/accounts/bluesky", response_model=str, include_in_schema=False
)
async def get_beamline_bluesky_username(name: str):
    bluesky_user = await beamline_service.bluesky_username(name)
    if bluesky_user is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"No bluesky user has been defined for the {name.upper()} beamline",
        )
    return bluesky_user


@router.get(
    "/beamline/{name}/accounts/epics-services",
    response_model=str,
    include_in_schema=False,
)
async def get_beamline_epics_services_username(name: str):
    epics_user = await beamline_service.epics_services_username(name)
    if epics_user is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"No EPICS services user has been defined for the {name.upper()} beamline",
        )
    return epics_user


@router.get(
    "/beamline/{name}/accounts/operator", response_model=str, include_in_schema=False
)
async def get_beamline_operator_username(name: str):
    operator_user = await beamline_service.operator_username(name)
    if operator_user is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"No operator user has been defined for the {name.upper()} beamline",
        )
    return operator_user


@router.get(
    "/beamline/{name}/services",
    response_model=list[BeamlineService],
    include_in_schema=True,
)
async def get_beamline_services(name: str):
    beamline_services = await beamline_service.all_services(name)
    if beamline_services is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Beamline named {name.upper()} could not be found",
        )
    return beamline_services


@router.put(
    "/beamline/{name}/services/",
    include_in_schema=True,
    response_model=BeamlineService,
    dependencies=[Depends(validate_admin_role)],
)
async def add_beamline_service(name: str, service: BeamlineService):
    logger.info(f"Adding service {service.name} to beamline {name.upper()}")

    new_service = await beamline_service.add_service(
        beamline_name=name,
        service_name=service.name,
        used_in_production=service.used_in_production,
        host=service.host,
        port=service.port,
        uri=service.uri,
    )

    if new_service is None:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Service {service.name} already exists in beamline {name.upper()}",
        )

    return new_service


@router.get("/beamlines")
async def get_all_beamlines():
    """
    Get all beamlines.
    """
    beamlines = await beamline_service.all_beamlines()
    if not beamlines:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="No beamlines found",
        )
    return beamlines
