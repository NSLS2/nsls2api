from typing import Optional

import pydantic
from pydantic import ConfigDict


class PassPerson(pydantic.BaseModel):
    """
    This class represents PASS's representation of a Person (e.g. PI or Creator).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    Can_Edit: Optional[bool] = None
    Can_Read: Optional[bool] = None
    CoPI: Optional[bool] = None
    On_Site: Optional[bool] = None
    Pool_ID: Optional[int] = None
    Proposal_ID: Optional[int] = None
    User_ID: Optional[int] = None
    Account: Optional[str] = None
    BNL_ID: Optional[str] = None
    Email: Optional[str] = None
    First_Name: Optional[str] = None
    Last_Name: Optional[str] = None
    User_Facility_ID: Optional[str] = None


class PassAllocation(pydantic.BaseModel):
    """
    This class represents PASS's representation of an Allocation.
    """

    Expired: Optional[bool] = None
    Expiration_Date: Optional[str] = None
    Allocated_Proposal_Type_ID: Optional[int] = None
    Created_Proposal_Type_ID: Optional[int] = None
    Creator_User_ID: Optional[int] = None
    Cycle_Request_ID: Optional[int] = None
    Proposal_ID: Optional[int] = None
    PI_User_ID: Optional[int] = None
    PRP_Hours_Recommended: Optional[float] = None
    Total_Hours_Requested: Optional[float] = None
    Total_Hours_Awarded: Optional[float] = None
    Allocated_Proposal_Type_Description: Optional[str] = None
    Beamline_Description: Optional[str] = None
    Comments: Optional[str] = None
    Created_Proposal_Type_Description: Optional[str] = None
    Cycle_Requested_Description: Optional[str] = None
    Short_Name: Optional[str] = None
    Title: Optional[str] = None
    User_Facility_ID: Optional[str] = None
    Creator: Optional[PassPerson] = None
    PI: Optional[PassPerson] = None


class PassCycle(pydantic.BaseModel):
    """
    This class represents PASS's representation of a Cycle.
    """

    Active: Optional[bool] = None
    ID: Optional[int] = None
    Year: Optional[int] = None
    Start_Date: Optional[str] = None
    End_Date: Optional[str] = None
    Name: Optional[str] = None
    Description: Optional[str] = None
    User_Facility_ID: Optional[str] = None


class PassExperimenter(pydantic.BaseModel):
    """
    This class represents PASS's representation of an Experimenter.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    Can_Edit: Optional[bool] = None
    Can_Read: Optional[bool] = None
    CoPI: Optional[bool] = None
    On_Site: Optional[bool] = None
    Remote_Access: Optional[bool] = None
    Mail_In: Optional[bool] = None
    Off_Site: Optional[bool] = None
    Pool_ID: Optional[int] = None
    Proposal_ID: Optional[int] = None
    User_ID: Optional[int] = None
    Account: Optional[str] = None
    BNL_ID: Optional[str] = None
    Email: Optional[str] = None
    First_Name: Optional[str] = None
    Last_Name: Optional[str] = None
    User_Facility_ID: Optional[str] = None


class PassResource(pydantic.BaseModel):
    """
    This class represents PASS's representation of a Resource.
    """

    ID: Optional[int] = None
    Description: Optional[str] = None
    User_Facility_ID: Optional[str] = None
    Short_Name: Optional[str] = None


class PassProposalType(pydantic.BaseModel):
    """
    This class represents PASS's representation of a ProposalType.
    """

    ID: Optional[int] = None
    Code: Optional[str] = None
    Description: Optional[str] = None
    User_Facility_ID: Optional[str] = None


class PassProposal(pydantic.BaseModel):
    """
    This class represents PASS's representation of a Proposal.
    """

    Expired: Optional[bool] = None
    Expiration_Date: Optional[str] = None
    Creator_User_ID: Optional[int] = None
    Proposal_ID: Optional[int] = None
    Proposal_Type_ID: Optional[int] = None
    PI_User_ID: Optional[int] = None
    Proposal_Type_Description: Optional[str] = None
    Title: Optional[str] = None
    User_Facility_ID: Optional[str] = None
    Creator: Optional[PassPerson] = None
    PI: Optional[PassPerson] = None
    Experimenters: Optional[list[PassExperimenter]] = []
    Resources: Optional[list[PassResource]] = []


class PassScheduledTimeSFTK(pydantic.BaseModel):
    """
    This class represents PASS's representation of a ScheduledTimeSFTK.
    """

    ProposalID: Optional[int] = None
    CycleRequestedID: Optional[int] = None
    ResourceID: Optional[int] = None
    UserFacilityID: Optional[str] = None
    ExtSchedulerRecordID: Optional[str] = None
    ScheduledHoursDuration: Optional[float] = None
    StartTime: Optional[str] = None
    StopTime: Optional[str] = None
    AddedModifiedByUserID: Optional[int] = None
    DateAddedModified: Optional[str] = None


class PassSaf(pydantic.BaseModel):
    """
    This class represents PASS's representation of a SAF.
    """

    SAF_ID: Optional[int] = None
    Date_Expires: Optional[str] = None
    Status: Optional[str] = None
    Experimenters: Optional[list[PassExperimenter]] = []
    Resources: Optional[list[PassResource]] = []
