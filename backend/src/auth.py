import os
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY", "kredl-dev-key")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return api_key
