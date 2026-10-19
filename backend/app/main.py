import secrets
import string
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Link

ALPHABET = string.ascii_letters + string.digits


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # creates the table if missing
    yield


app = FastAPI(title="ShortLink API", lifespan=lifespan)


class LinkIn(BaseModel):
    url: HttpUrl  # rejects anything that is not a valid http(s) URL


class LinkOut(BaseModel):
    model_config = {"from_attributes": True}
    code: str
    url: str
    clicks: int


def new_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(6))
        if not db.scalar(select(Link).where(Link.code == code)):
            return code


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/links", response_model=LinkOut, status_code=201)
def create_link(body: LinkIn, db: Session = Depends(get_db)):
    link = Link(code=new_code(db), url=str(body.url), clicks=0)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@app.get("/api/links", response_model=list[LinkOut])
def list_links(db: Session = Depends(get_db)):
    return db.scalars(select(Link).order_by(Link.id.desc()).limit(50)).all()


@app.get("/r/{code}")
def follow(code: str, db: Session = Depends(get_db)):
    link = db.scalar(select(Link).where(Link.code == code))
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    link.clicks += 1
    db.commit()
    return RedirectResponse(link.url, status_code=307)