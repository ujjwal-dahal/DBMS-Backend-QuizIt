from fastapi import FastAPI
from authentication.main import app as auth_router

router = FastAPI()


@router.get("/", tags=["Index"])
def index_page():
    return {"message": "This is Main Page"}


router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
