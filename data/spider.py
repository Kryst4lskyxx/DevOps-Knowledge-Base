import datetime
import requests
import json
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD

# Define the ontology namespace
namespace = Namespace("http://www.semanticweb.org/yeyuan/ontologies/dt_lifecycle/")

# Define tools categories
planning_tools = ["jira", "maven", "gradle", "trello", "miro"]
development_tools = ["docker", "maven", "npm"]
testing_tools = ["junit", "jmeter", "selenium", "testng"]
cicd_tools = ["jenkins", "bamboo", "actions"]
deployment_tools = ["ansible", "docker", "vagrant", "terraform", "kubernetes"]
monitoring_tools = ["kibana", "datadog", "prometheus"]

def get_project_info(owner, repo):
    
    url = f"https://api.github.com/repos/{owner}/{repo}/dependency-graph/sbom"
    #Replace it with your token
    headers = {"Authorization": f"Bearer {"access_token"}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        sbom_info = response.json()
        stake_holder = owner
        project_name = repo
        sbom_packages = sbom_info['sbom']['packages']
        
        project_tools = []
        devops_lifecycle_stage = 'Planning'  # Default stage
        
        for package in sbom_packages:
            package_name = package['name']
            for tool in planning_tools:
                if tool in package_name:
                    project_tools.append(tool)
                    devops_lifecycle_stage = 'Planning'
            for tool in development_tools:
                if tool in package_name:
                    project_tools.append(tool)
                    devops_lifecycle_stage = 'Development'
            for tool in testing_tools:
                if tool in package_name:
                    project_tools.append(tool)
                    devops_lifecycle_stage = 'Testing'
            for tool in cicd_tools:
                if tool in package_name:
                    project_tools.append(tool)
                    devops_lifecycle_stage = 'CI/CD'
            for tool in deployment_tools:
                if tool in package_name:
                    project_tools.append(tool)
                    devops_lifecycle_stage = 'Deployment'
            for tool in monitoring_tools:
                if tool in package_name:
                    project_tools.append(tool)
                    devops_lifecycle_stage = 'Monitoring'
        
        project_tools = list(set(project_tools))
        return stake_holder, project_name, devops_lifecycle_stage, project_tools
    else:
        print("Failed to retrieve project information.")
        return None

def create_ontology_instance(stake_holder, project_name, lifecycle_stage, tools):
    g = Graph()
    g.bind("dtl", namespace)
    
    # Create Project instance
    project_uri = URIRef(namespace + project_name)
    g.add((project_uri, RDF.type, namespace.Project))
    g.add((project_uri, namespace.name, Literal(project_name, datatype=XSD.string)))

    # Create Stakeholder instance
    stakeholder_uri = URIRef(namespace + stake_holder)
    g.add((stakeholder_uri, RDF.type, namespace.Stakeholder))
    g.add((stakeholder_uri, namespace.name, Literal(stake_holder, datatype=XSD.string)))
    g.add((project_uri, namespace.ownedBy, stakeholder_uri))

    # Create Lifecycle Phase instance
    phase_uri = URIRef(namespace + lifecycle_stage)
    g.add((phase_uri, RDF.type, namespace.DevOpsLifecyclePhase))
    g.add((phase_uri, namespace.name, Literal(lifecycle_stage, datatype=XSD.string)))
    g.add((project_uri, namespace.isInTheStageOf, phase_uri))
    
    # Link tools to the project
    for tool in tools:
        tool_uri = URIRef(namespace + tool)
        g.add((tool_uri, RDF.type, namespace.DevOpsTool))
        g.add((tool_uri, namespace.name, Literal(tool, datatype=XSD.string)))
        g.add((project_uri, namespace.utilizes, tool_uri))
    
    return g

def save_ttl_file(graph, filename):
    graph.serialize(destination=filename, format='turtle')

# Example usage:
project_list = [["cambridge-cares", "TheWorldAvatar"],
                ["neo4j-labs", "rdflib-neo4j"]]

for project in project_list:
    
    stake_holder, project_name, lifecycle_stage, tools = get_project_info(project[0], project[1])
    if stake_holder:
        g = create_ontology_instance(stake_holder, project_name, lifecycle_stage, tools)
        save_ttl_file(g, f"data/project_info/{project_name}_ontology.ttl")
        print(f"Ontology saved as {project_name}_ontology.ttl")

print("Done!")