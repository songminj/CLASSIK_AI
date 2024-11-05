from typing import Union
from chatbot import text_embed
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/{content}")
def ai_content(content : str):
    result = text_embed(content)
    return {"result" : result}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}