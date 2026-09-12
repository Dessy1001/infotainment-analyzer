
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .backend.database import Base, engine
from .backend.routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Информационна система за анализ на инфотейнмънт системи")
app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")
app.include_router(router)
