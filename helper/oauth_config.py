from authlib.integrations.starlette_client import OAuth
from helper.config import (
    SERVICE_METADATA_URL,
    CLIENT_ID,
    CLIENT_SECRET,
)

oauth = OAuth()

oauth.register(
    name="google",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url=SERVICE_METADATA_URL,
    client_kwargs={"scope": "openid email profile"},
)
