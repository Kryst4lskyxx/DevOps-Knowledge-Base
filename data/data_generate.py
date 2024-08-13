from rdflib_neo4j import Neo4jStoreConfig, Neo4jStore, HANDLE_VOCAB_URI_STRATEGY
from rdflib import Graph
import os

prefixes = {
    "dtl": "http://www.semanticweb.org/yeyuan/ontologies/dt_lifecycle/",
    "xsd": "http://www.w3.org/2001/XMLSchema#"
}

# set the configuration to connect to your Aura DB
AURA_DB_URI="bolt://localhost:7687"
AURA_DB_USERNAME="neo4j"
AURA_DB_PWD="12345678"

auth_data = {'uri': AURA_DB_URI,
             'database': "neo4j",
             'user': AURA_DB_USERNAME,
             'pwd': AURA_DB_PWD}

# Define your custom mappings & store config
config = Neo4jStoreConfig(auth_data=auth_data,
                          custom_prefixes=prefixes,
                          handle_vocab_uri_strategy=HANDLE_VOCAB_URI_STRATEGY.IGNORE,
                          batching=True)

def get_file_paths(directory):
    file_paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)
    return file_paths

directory = "data/project_info"  
file_paths = get_file_paths(directory)

# Create the RDF Graph, parse & ingest the data to Neo4j, and close the store(If the field batching is set to True in the Neo4jStoreConfig, remember to close the store to prevent the loss of any uncommitted records.)
neo4j_aura = Graph(store=Neo4jStore(config=config))
# Calling the parse method will implictly open the store
for file in file_paths:
    neo4j_aura.parse(file, format="ttl")
neo4j_aura.close(True)
