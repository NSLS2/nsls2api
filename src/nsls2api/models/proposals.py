import datetime
from typing import Optional

import beanie
import pydantic
import pymongo


class SafetyForm(pydantic.BaseModel):
    saf_id: str
    status: str
    instruments: Optional[list[str]]


class User(pydantic.BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    bnl_id: Optional[str] = None
    username: Optional[str] = None
    is_pi: bool = False


class Proposal(beanie.Document):
    proposal_id: str
    data_session: str
    title: Optional[str] = None
    type: Optional[str] = None
    pass_type_id: Optional[str] = None
    facility: str
    instruments: Optional[list[str]] = []
    cycles: Optional[list[str]] = []
    users: Optional[list[User]] = []
    safs: Optional[list[SafetyForm]] = []
    slack_channel_id: Optional[str] = None
    created_on: datetime.datetime = pydantic.Field(
        default_factory=datetime.datetime.now
    )
    last_updated: datetime.datetime = pydantic.Field(
        default_factory=datetime.datetime.now
    )

    class Settings:
        name = "proposals"
        indexes = [
            pymongo.IndexModel(
                keys=[("proposal_id", pymongo.DESCENDING)],
                name="proposal_id_descend",
            ),
            pymongo.IndexModel(
                keys=[("last_updated", pymongo.DESCENDING)],
                name="last_updated_descend",
            ),
            pymongo.IndexModel(
                keys=[("users.username", pymongo.ASCENDING)],
                name="users_username_ascend",
            ),
            pymongo.IndexModel(
                keys=[("users.email", pymongo.ASCENDING)],
                name="users_email_ascend",
            ),
            pymongo.IndexModel(
                keys=[("users.bnl_id", pymongo.ASCENDING)],
                name="users_bnl_id_ascend",
            ),
            pymongo.IndexModel(
                keys=[("users.last_name", pymongo.ASCENDING)],
                name="users_last_name_ascend",
            ),
            pymongo.IndexModel(
                keys=[("safs.saf_id", pymongo.DESCENDING)],
                name="safs_saf_id_descend",
            ),
            pymongo.IndexModel(
                keys=[
                    ("proposal_id", pymongo.TEXT),
                    ("data_session", pymongo.TEXT),
                    ("safs.saf_id", pymongo.TEXT),
                    ("facility", pymongo.TEXT),
                    ("instruments", pymongo.TEXT),
                    ("cycles", pymongo.TEXT),
                    ("title", pymongo.TEXT),
                ],
                name="proposals_full_text",
            ),
        ]


class UsernamesOnly(pydantic.BaseModel):
    username: str

    class Settings:
        projection = {
            "username": "$username",
        }


class ProposalIdView(pydantic.BaseModel):
    proposal_id: str

    class Settings:
        projection = {"proposal_id": "$proposal_id"}
