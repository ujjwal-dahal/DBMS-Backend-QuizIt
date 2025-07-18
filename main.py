from fastapi import FastAPI
from app.authentication.main import app as auth_router
from app.users.main import router as user_router
from app.quiz.main import app as quiz_app

router = FastAPI()


@router.get("/", tags=["Index"])
def index_page():
    return {"message": "This is Main Page"}


router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(user_router, prefix="/user", tags=["User"])
router.include_router(quiz_app, prefix="/quiz", tags=["Quiz"])
