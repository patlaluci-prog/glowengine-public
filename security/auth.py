from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKey

from config import (
    API_KEY,
    api_key_header
)


def verify_api_key(
    api_key: APIKey = Security(api_key_header)
):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )

    return api_key