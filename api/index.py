# FastAPI Imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Projects Import
from app.authentication.main import app as auth_router
from app.users.main import router as user_router
from app.quiz.main import app as quiz_app
from app.websocket.main import app as websocket_app
from app.features.main import app as features_app

app = FastAPI()


@app.get("/", tags=["Index"])
def index_page():
    return {
        "message": "QuizIt API",
        "Backend Developer": "Ujjwal Dahal",
        "Frontend Developer": "Dharmananda Joshi",
    }


app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(quiz_app, prefix="/quiz", tags=["Quiz"])
app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(websocket_app, prefix="/room", tags=["WebSocket"])
app.include_router(features_app, tags=["Features"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
