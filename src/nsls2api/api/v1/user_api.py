from typing import Annotated

import fastapi
from fastapi import Depends

from nsls2api.api.models.person_model import DataSessionAccess, Person
from nsls2api.infrastructure.security import (
    get_current_user,
)
from nsls2api.services import (
    bnlpeople_service,
    person_service,
)

router = fastapi.APIRouter()


@router.get("/person/username/{username}", response_model=Person)
async def get_person_from_username(username: str):
    bnl_person = await bnlpeople_service.get_person_by_username(username)
    print(bnl_person)
    if bnl_person:
        person = Person(
            firstname=bnl_person.FirstName,
            lastname=bnl_person.LastName,
            email=bnl_person.BNLEmail,
            bnl_id=bnl_person.EmployeeNumber,
            institution=bnl_person.Institution,
            username=bnl_person.ActiveDirectoryName,
            cyber_agreement_signed=bnl_person.CyberAgreementSigned,
        )
        # If the person is an Employee then set their institution to BNL
        if (
            bnl_person.EmployeeStatus == "Active"
            and bnl_person.EmployeeType == "Employee"
        ):
            person.bnl_employee = True
            person.institution = "Brookhaven National Laboratory"
        return person
    else:
        return fastapi.responses.JSONResponse(
            {"error": f"No people with username {username} found."},
            status_code=404,
        )


@router.get("/person/email/{email}")
async def get_person_from_email(email: str):
    bnl_person = await bnlpeople_service.get_person_by_email(email)
    if bnl_person:
        person = Person(
            firstname=bnl_person.FirstName,
            lastname=bnl_person.LastName,
            email=bnl_person.BNLEmail,
            bnl_id=bnl_person.EmployeeNumber,
            institution=bnl_person.Institution,
            username=bnl_person.ActiveDirectoryName,
            cyber_agreement_signed=bnl_person.CyberAgreementSigned,
        )
        return person
    else:
        return fastapi.responses.JSONResponse(
            {"error": f"No people with username {email} found."},
            status_code=404,
        )


# TODO: Add back into schema if we decide to use this endpoint.
@router.get("/person/department/{department}", include_in_schema=False)
async def get_person_by_department(department_code: str = "PS"):
    bnl_people = await bnlpeople_service.get_people_by_department(department_code)
    if bnl_people:
        return bnl_people


# TODO: Add back into schema if we decide to use this endpoint.
@router.get("/person/me", response_model=str, include_in_schema=False)
async def get_myself(current_user: Annotated[Person, Depends(get_current_user)]):
    return current_user


@router.get("/data-session/{username}", response_model=DataSessionAccess, tags=["data"])
@router.get(
    "/data_session/{username}",
    response_model=DataSessionAccess,
    tags=["data"],
    include_in_schema=True,
    description="Deprecated endpoint included for Tiled compatibility.",
    deprecated=True,
)
async def get_data_sessions_by_username(username: str):
    data_access = await person_service.data_sessions_by_username(username)
    return data_access
