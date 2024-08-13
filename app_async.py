#!/usr/bin/env python
import logging
import os
from contextlib import asynccontextmanager
from textwrap import dedent
from typing import Optional, cast

import neo4j
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from neo4j import AsyncGraphDatabase
from typing_extensions import LiteralString


PATH = os.path.dirname(os.path.abspath(__file__))


url = os.getenv("NEO4J_URI", "bolt://localhost:7687")
username = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "12345678")
neo4j_version = os.getenv("NEO4J_VERSION", "5")
database = os.getenv("NEO4J_DATABASE", "neo4j")

port = int(os.getenv("PORT", 8080))

shared_context = {}


def query(q: LiteralString) -> LiteralString:
    # this is a safe transform:
    # no way for cypher injection by trimming whitespace
    # hence, we can safely cast to LiteralString
    return cast(LiteralString, dedent(q).strip())


@asynccontextmanager
async def lifespan(app: FastAPI):
    driver = AsyncGraphDatabase.driver(url, auth=(username, password))
    shared_context["driver"] = driver
    yield
    await driver.close()


def get_driver() -> neo4j.AsyncDriver:
    return shared_context["driver"]


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def get_index():
    return FileResponse(os.path.join(PATH, "static", "index.html"))


def serialize_result(res):
    return {
        # "id": res["id"],
        "name": res["name"],
        "uri": res["uri"]
    }

def serialize_info(info):
    return{
        "p_name": info[0],
        "relation": info[1],
        "n_name": info[2]
    }


@app.get("/graph")
async def get_graph(limit: int = 100):
    records, _, _ = await get_driver().execute_query(
        query("""
            MATCH (a:DevOpsTool) <-[:utilizes]-(m:Project)
            RETURN m.name AS project, collect(a.name) AS tool
            LIMIT $limit
        """),
        database_=database,
        routing_="r",
        limit=limit,
    )
    nodes = []
    rels = []
    i = 0
    for record in records:
        nodes.append({"name": record["project"], "label": "project"})
        target = i
        i += 1
        for name in record["tool"]:
            tool = {"name": name, "label": "tool"}
            try:
                source = nodes.index(tool)
            except ValueError:
                nodes.append(tool)
                source = i
                i += 1
            rels.append({"source": source, "target": target})
    return {"nodes": nodes, "links": rels}


@app.get("/search")
async def get_search(q: Optional[str] = None):
    if q is None:
        return []
    records, _, _ = await get_driver().execute_query(
        query("""
                MATCH (project:Project)
                WHERE toLower(project.name) CONTAINS toLower($name)
                RETURN project
            """),
        name=q,
        database_=database,
        routing_="r",
    )
    return [serialize_result(record["project"]) for record in records]


@app.get("/project/{name}")
async def get_movie(name: str):
    result = await get_driver().execute_query(
        query("""
            MATCH (p:Project {name: $name})-[r]-(n) 
            RETURN p.name as name, COLLECT([p.name, type(r), n.name]) as info
        """),
        name=name,
        database_=database,
        routing_="r",
        result_transformer_=neo4j.AsyncResult.single,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"name": result["name"],
            "info": [serialize_info(info)
                     for info in result["info"]]}


# @app.post("/movie/{title}/vote")
# async def vote_in_movie(title: str):
#     summary = await get_driver().execute_query(
#         query("""
#             MATCH (m:Movie {title: $title})
#             SET m.votes = coalesce(m.votes, 0) + 1;
#         """),
#         database_=database,
#         title=title,
#         result_transformer_=neo4j.AsyncResult.consume,
#     )
#     updates = summary.counters.properties_set

#     return {"updates": updates}


if __name__ == "__main__":
    import uvicorn

    logging.root.setLevel(logging.INFO)
    logging.info("Starting on port %d, database is at %s", port, url)

    uvicorn.run(app, port=port)
