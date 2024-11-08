from fastapi import FastAPI
from domain.search import router as search_router
from domain.skybox import router as skybox_router

app = FastAPI()

app.include_router(search_router.router)
app.include_router(skybox_router.router)