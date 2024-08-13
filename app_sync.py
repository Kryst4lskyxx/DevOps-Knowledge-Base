#!/usr/bin/env python
import logging
import os
from json import dumps
from textwrap import dedent
from typing import cast

import neo4j
from flask import Flask, Response, request
from neo4j import GraphDatabase, basic_auth
from typing_extensions import LiteralString

app = Flask(__name__, static_url_path="/static/")

url = os.getenv("NEO4J_URI", "bolt://localhost:7687")
username = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "12345678")
neo4j_version = os.getenv("NEO4J_VERSION", "5")
database = os.getenv("NEO4J_DATABASE", "neo4j")

port = int(os.getenv("PORT", 8080))

driver = GraphDatabase.driver(url, auth=basic_auth(username, password))


def query(q: LiteralString) -> LiteralString:
    # this is a safe transform:
    # no way for cypher injection by trimming whitespace
    # hence, we can safely cast to LiteralString
    return cast(LiteralString, dedent(q).strip())


@app.route("/")
def get_index():
    return app.send_static_file("index.html")


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

@app.route("/graph")
def get_graph():
    records, _, _ = driver.execute_query(
        query("""
            MATCH (a:DevOpsTool) <-[:utilizes]-(m:Project)
            RETURN m.name AS project, collect(a.name) AS tool
            LIMIT $limit
        """),
        database_=database,
        routing_="r",
        limit=request.args.get("limit", 100)
    )
    nodes = []
    rels = []
    i = 0
    for record in records:
        nodes.append({"project": record["project"], "label": "project"})
        target = i
        i += 1
        for name in record["tool"]:
            tool = {"tool": name, "label": "tool"}
            try:
                source = nodes.index(tool)
            except ValueError:
                nodes.append(tool)
                source = i
                i += 1
            rels.append({"source": source, "target": target})
    return Response(dumps({"nodes": nodes, "links": rels}),
                    mimetype="application/json")


@app.route("/search")
def get_search():
    try:
        q = request.args["q"]
    except KeyError:
        return []
    else:
        records, _, _ = driver.execute_query(
            query("""
                MATCH (project:Project)
                WHERE toLower(project.name) CONTAINS toLower($name)
                RETURN project
            """),
            name=q,
            database_=database,
            routing_="r",
        )
        return Response(
            dumps([serialize_result(record["project"]) for record in records]),
            mimetype="application/json"
        )


@app.route("/project/<name>")
def get_project(name):
    result = driver.execute_query(
        query("""
            MATCH (p:Project {name: $name})-[r]-(n) 
            RETURN p.name as name, COLLECT([p.name, type(r), n.name]) as info
        """),
        name=name,
        database_=database,
        routing_="r",
        result_transformer_=neo4j.Result.single,
    )
    if not result:
        return Response(dumps({"error": "project not found"}), status=404,
                        mimetype="application/json")

    return Response(dumps({"name": result["name"],
                           "info": [serialize_info(info)
                                    for info in result["info"]]}),
                    mimetype="application/json")


# @app.route("/project/<title>/vote", methods=["POST"])
# def vote_in_project(title):
#     summary = driver.execute_query(
#         query("""
#             MATCH (m:project {title: $title})
#             SET m.votes = coalesce(m.votes, 0) + 1;
#         """),
#         database_=database,
#         title=title,
#         result_transformer_=neo4j.Result.consume,
#     )
#     updates = summary.counters.properties_set
#     return Response(dumps({"updates": updates}), mimetype="application/json")


if __name__ == "__main__":
    logging.root.setLevel(logging.INFO)
    logging.info("Starting on port %d, database is at %s", port, url)
    try:
        app.run(port=port)
    finally:
        driver.close()
