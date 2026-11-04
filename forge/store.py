import json, os
from pathlib import Path
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Text,
    select,
    update,
)


class Store:
    def __init__(self, url=None):
        if url is None:
            Path("runtime").mkdir(exist_ok=True)
            url = os.environ.get("DATABASE_URL", "sqlite:///runtime/forge.db")
        self.engine = create_engine(
            url,
            connect_args=(
                {"check_same_thread": False} if url.startswith("sqlite") else {}
            ),
        )
        meta = MetaData()
        self.runs = Table(
            "runs",
            meta,
            Column("id", String(32), primary_key=True),
            Column("payload", Text, nullable=False),
        )
        meta.create_all(self.engine)

    def save(self, data):
        with self.engine.begin() as c:
            exists = c.execute(
                select(self.runs.c.id).where(self.runs.c.id == data["id"])
            ).first()
            if exists:
                c.execute(
                    update(self.runs)
                    .where(self.runs.c.id == data["id"])
                    .values(payload=json.dumps(data))
                )
            else:
                c.execute(
                    self.runs.insert().values(id=data["id"], payload=json.dumps(data))
                )

    def get(self, id):
        with self.engine.connect() as c:
            row = c.execute(
                select(self.runs.c.payload).where(self.runs.c.id == id)
            ).first()
            return json.loads(row[0]) if row else None

    def list(self):
        with self.engine.connect() as c:
            rows = c.execute(select(self.runs.c.payload)).all()
        return sorted(
            [json.loads(r[0]) for r in rows], key=lambda x: x["created"], reverse=True
        )[:100]

    def recover(self):
        for r in self.list():
            if r["status"] in ("queued", "running"):
                r.update(
                    status="interrupted", error="Server restarted. Start a new run."
                )
                self.save(r)
