from pydantic import BaseModel


class WsEnvelope(BaseModel):
    v: int = 1
    type: str
    payload: dict | None = None
    request_id: str | None = None
    topic: str | None = None
    ts: str | None = None