from pymongo.operations import SearchIndexModel
from config import settings
from database import get_db

VECTOR_INDEX_NAME = "trial_match_vector"

def main() -> None:
    db = get_db()

    db.trial_sites.create_index([("location", "2dsphere")])
    db.trial_sites.create_index("trialId")
    print("Created/confirmed trial_sites indexes.")

    existing = {
        item.get("name")
        for item in db.trial_chunks.list_search_indexes()
    }

    if VECTOR_INDEX_NAME in existing:
        print(f"Vector Search index already exists: {VECTOR_INDEX_NAME}")
        return

    model = SearchIndexModel(
        definition={
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": settings.voyage_dimensions,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "trialId"},
                {"type": "filter", "path": "minAge"},
                {"type": "filter", "path": "maxAge"},
                {"type": "filter", "path": "stage"},
                {"type": "filter", "path": "status"},
            ]
        },
        name=VECTOR_INDEX_NAME,
        type="vectorSearch",
    )

    name = db.trial_chunks.create_search_index(model=model)
    print(f"Requested Vector Search index creation: {name}")
    print("Atlas builds Search indexes asynchronously; wait until READY before querying.")

if __name__ == "__main__":
    main()
