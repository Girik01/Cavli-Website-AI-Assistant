import json, os, sys, time, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # lets `python app/main.py` find the app package
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

from app import config, guard  # noqa: E402
from ingest.cavli26 import CATEGORIES, CONTACT_URL, MODULE_PAGES, category_url  # noqa: E402

from contextlib import asynccontextmanager  # noqa: E402
from app import rag  # noqa: E402


@asynccontextmanager
async def lifespan(_):
    rag.warm()   # load the keyword index once at startup so the first question is fast
    yield


app = FastAPI(title="Cavli Website Assistant (PoC)", lifespan=lifespan)
# Same-origin by default. To embed on another site, add its origin to ALLOWED_ORIGINS in app/config.py.
app.add_middleware(CORSMiddleware, allow_origins=config.ALLOWED_ORIGINS, allow_methods=["POST", "GET"], allow_headers=["Content-Type"])
LATENCIES: list = []
from collections import defaultdict, deque  # noqa: E402
HITS = defaultdict(deque)
CATEGORY_NAMES = [v[0] for v in CATEGORIES.values()]
RATE = config.RATE_LIMIT_PER_MIN


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=config.MAX_QUESTION_CHARS)


class FeedbackIn(BaseModel):
    request_id: str
    rating: int = Field(ge=-1, le=1)  # 1 = helpful, -1 = not helpful
    comment: str = Field(default="", max_length=500)


import re  # noqa: E402
_PII = [(re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"), (re.compile(r"\+?\d[\d\s().-]{7,}\d"), "[phone]")]


def redact(text, tag=True):
    """tag=True for logs ("[email]"); tag=False removes the PII entirely (used before retrieval / the LLM)."""
    for rx, label in _PII:
        text = rx.sub(label if tag else "", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def log(name, rec):
    with open(DATA / name, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _early(question, t0):
    """Replies that need no retrieval and no LLM call. Returns a dict or None."""
    base = {"inference": "", "citations": [], "unverified": [], "follow_up_question": "", "top_score": 0}
    if guard.smalltalk(question):
        return {**base, "kind": "smalltalk", "supported": False, "answer": guard.smalltalk(question), "links": []}
    if guard.clarify(question):
        return {**base, "kind": "clarify", "supported": False, "answer": guard.CLARIFY,
                "links": [{"title": f"{c} modules", "url": category_url(c)} for c in CATEGORY_NAMES]}
    if guard.commercial(question):
        mods = [m for m in MODULE_PAGES if m.lower() in question.lower().replace(" ", "")]
        return {**base, "kind": "not_verified", "supported": False, "answer": guard.NOT_VERIFIED_COMMERCIAL,
                "links": [{"title": f"{m} product page", "url": MODULE_PAGES[m]} for m in mods]
                         + [{"title": "Contact the Cavli team", "url": CONTACT_URL}]}
    blocked = guard.check(question)
    if blocked:
        return {**base, "kind": "blocked", "blocked": blocked, "supported": False, "answer": guard.REFUSAL,
                "links": [{"title": "Contact the Cavli team", "url": CONTACT_URL}]}
    return None


def _rate_limit(request):
    ip, now = (request.client.host if request.client else "?"), time.time()
    q = HITS[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE:
        raise HTTPException(429, detail={"message": "Too many requests. Please wait a minute and try again."})
    q.append(now)


def _events(question, rid, t0):
    """Yield events for one question; the last one is always `final` (with request_id and latency)."""
    def done(d, timing=None):
        total = round((time.perf_counter() - t0) * 1000)
        d["request_id"] = rid
        d["latency_ms"] = {"retrieval": 0, "first_token": None, "llm": 0, **(timing or {}), "total": total}
        if d["kind"] in ("answer", "not_verified", "out_of_scope"):
            LATENCIES.append(total)
        log("requests.jsonl", {"request_id": rid, "question": redact(question), "kind": d["kind"],
                               "top_score": d.get("top_score"), "latency_ms": d["latency_ms"]})
        return {"type": "final", **d}

    early = _early(question, t0)
    if early:
        yield done(early)
        return
    try:
        for ev in rag.run(redact(question.strip(), tag=False)):   # PII never reaches retrieval or the LLM
            if ev["type"] == "final":
                ev = dict(ev)
                timing = {k: ev.pop(k) for k in ("retrieval", "first_token", "llm") if k in ev}
                ev.pop("type")
                yield done(ev, timing)
            else:
                yield ev
    except Exception as e:  # never leak internals or keys
        log("requests.jsonl", {"request_id": rid, "error": type(e).__name__})
        yield {"type": "error", "message": "The assistant is temporarily unavailable. Please try again or contact "
               "the Cavli team.", "contact": CONTACT_URL}


@app.post("/api/chat")
def chat(body: ChatIn, request: Request):
    """Non-streaming: returns only the final result."""
    _rate_limit(request)
    last = None
    for ev in _events(body.question, uuid.uuid4().hex[:12], time.perf_counter()):
        last = ev
    if last["type"] == "error":
        raise HTTPException(503, detail={"message": last["message"], "contact": last["contact"]})
    last.pop("type")
    return last


@app.post("/api/chat/stream")
def chat_stream(body: ChatIn, request: Request):
    """Server-sent events: sources -> cite/token ... -> final. First tokens arrive as soon as the model emits them."""
    _rate_limit(request)

    def gen():
        for ev in _events(body.question, uuid.uuid4().hex[:12], time.perf_counter()):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/feedback")
def feedback(body: FeedbackIn):
    log("feedback.jsonl", {**body.model_dump(), "ts": time.time()})
    return {"ok": True}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/metrics")
def metrics():
    if not LATENCIES:
        return {"requests": 0}
    s = sorted(LATENCIES)
    return {"requests": len(s), "avg_ms": round(sum(s) / len(s)), "p50_ms": round(s[len(s) // 2]),
            "p95_ms": round(s[min(len(s) - 1, int(len(s) * 0.95))])}


app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "frontend" / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=False)
