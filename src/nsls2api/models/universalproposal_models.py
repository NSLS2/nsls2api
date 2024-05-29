import pydantic

from pydantic import ConfigDict

class ServiceNowValue(pydantic.BaseModel):
    value: str
    display_value: str

class ServiceNowValueWithLink(ServiceNowValue):
    link: str | None = None

class UpsCycle(pydantic.BaseModel):
    """
    Representation of the sn_customerservice_run_cycle table.
    """
    sys_created_on: ServiceNowValue
    sys_id: ServiceNowValue
    sys_mod_count: ServiceNowValue
    sys_tags: ServiceNowValue
    sys_updated_on: ServiceNowValue
    u_active: ServiceNowValue
    u_end_date: ServiceNowValue
    u_facility: ServiceNowValueWithLink
    u_name: ServiceNowValue
    u_number: ServiceNowValue
    u_start_date: ServiceNowValue
    u_title: ServiceNowValue

class UpsProposalType(pydantic.BaseModel):
    sys_created_on: ServiceNowValue
    sys_id: ServiceNowValue
    sys_mod_count: ServiceNowValue
    sys_tags: ServiceNowValue
    sys_updated_on: ServiceNowValue
    u_name: ServiceNowValue
    u_active: ServiceNowValue
    u_facility: ServiceNowValueWithLink
    u_proposal_review_required: ServiceNowValue
    u_type: ServiceNowValue


class UpsProposalRecord(pydantic.BaseModel):
    sys_class_name: ServiceNowValue
    sys_created_on: ServiceNowValue
    sys_id: ServiceNowValue
    sys_mod_count: ServiceNowValue
    sys_tags: ServiceNowValue
    sys_updated_on: ServiceNowValue
    u_abstract_of_proposed_research: ServiceNowValue
    u_active: ServiceNowValue
    u_age_count: ServiceNowValue
    u_co_proposers: ServiceNowValue
    u_contributor_users: ServiceNowValue
    u_display_name: ServiceNowValue
    u_etr_created: ServiceNowValue | None = None
    u_etr_questions_completed: ServiceNowValue | None = None
    u_etr_reviews_completed: ServiceNowValue | None = None
    u_expiration_date: ServiceNowValue
    u_expired: ServiceNowValue
    u_keywords: ServiceNowValue
    u_number: ServiceNowValue
    u_other_subject_of_research: ServiceNowValue
    u_primary_subject_of_research: ServiceNowValue
    u_principal_investigator_pi: ServiceNowValueWithLink
    u_progression_steps: ServiceNowValue
    u_project_created: ServiceNowValue
    u_proposal_call: ServiceNowValueWithLink
    u_proposal_id: ServiceNowValue
    u_proposal_number: ServiceNowValue
    u_proposal_questions_complete: ServiceNowValue
    u_proposal_submitter: ServiceNowValue
    u_proposal_type: ServiceNowValueWithLink
    u_proprietary: ServiceNowValue
    u_review_status: ServiceNowValue
    u_status: ServiceNowValue
    u_submission_date: ServiceNowValue
    u_supporting_documentation: ServiceNowValue
    u_title: ServiceNowValue