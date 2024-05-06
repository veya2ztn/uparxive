from elasticsearch import Elasticsearch
ES_INDEX="integrate20240311"
es = Elasticsearch("http://localhost:9200")
es.indices.refresh()
# Configuration
repository_name           = 'digital_resource_paper'
snapshot_name             = 'semantic_scholar+crossref+arxiv+short_citation'
snapshot_repo_location    = "/var/lib/elasticsearch/repo"
indices_to_snapshot       = ES_INDEX

# Create the Elasticsearch client instances for the source and destination
source_es = es
# Register a Snapshot Repository on the source
source_es.snapshot.create_repository(
    name=repository_name,
    body={
        "type": "fs",
        "settings": {
            "location": snapshot_repo_location,
            "compress": True
        }
    }
)

# Create a Snapshot on the source
source_es.snapshot.create(
    repository=repository_name,
    snapshot=snapshot_name,
    body={
        "indices": indices_to_snapshot,
        "ignore_unavailable": True,
        "include_global_state": False
    },
    wait_for_completion=True  # Block until the snapshot is complete
)

print(f"Snapshot {snapshot_name} created successfully.")