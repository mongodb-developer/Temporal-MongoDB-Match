from temporalio import activity

import config

@activity.defn(name="embed_patient_query")
def embed_patient_query(extracted: dict) -> list[float]:
    if not config.VOYAGE_API_KEY:
        raise RuntimeError("VOYAGE_API_KEY is not set")

    client = config.voyage_client
    result = client.embed(
        [extracted["searchText"]],
        model=config.VOYAGE_MODEL,
        input_type="query",
        output_dimension=config.VOYAGE_DIMENSIONS,
    )
    return result.embeddings[0]
