from fastapi import APIRouter, Depends, Request, Query
from nsls2api.services.ldap_service import get_user_info
router = APIRouter()
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path="src/nsls2api/.env")
@router.get("/whoami")
async def whoami(request: Request, upn: str = Query(..., description="User Principal Name")):
    LDAP_SERVER = os.getenv("LDAP_SERVER")
    BASE_DN = os.getenv("BASE_DN")
    BIND_USER = os.getenv("BIND_USER")
    BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD")
    

    user_info = get_user_info(upn, LDAP_SERVER, BASE_DN, BIND_USER, BIND_PASSWORD)
    return {"user": user_info}