# backend/app.py
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from backend.session_store import get_session
from backend.graph import build_graph

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # OK for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = build_graph()


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    active_flow: str | None = None
    awaiting_field: str | None = None


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # 1. Load session-bound conversation state
    convo_state = get_session(req.session_id)

    # 2. Invoke agent graph
    result = graph.invoke({
        "convo_state": convo_state,
        "user_input": req.message,
        "bot_reply": "",
    })

    # 3. Return minimal agent-aware response
    return ChatResponse(
        reply=result["bot_reply"],
        active_flow=convo_state.active_flow,
        awaiting_field=convo_state.awaiting_field,
    )
