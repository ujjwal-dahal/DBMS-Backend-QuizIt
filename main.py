from fastapi import FastAPI
from authentication.main import app as auth_router
from users.main import router as user_router

router = FastAPI()


@router.get("/", tags=["Index"])
def index_page():
    return {"message": "This is Main Page"}


router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(user_router, prefix="/user", tags=["User"])
