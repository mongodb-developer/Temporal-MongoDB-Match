from temporalio import activity
import voyageai

from config import settings

@activity.defn(name="embed_patient_query")
def embed_patient_query(extracted: dict) -> list[float]:
    if not settings.voyage_api_key:
        raise RuntimeError("VOYAGE_API_KEY is not set")

    client = voyageai.Client(api_key=settings.voyage_api_key)
    result = client.embed(
        [extracted["searchText"]],
        model=settings.voyage_model,
        input_type="query",
        output_dimension=settings.voyage_dimensions,
    )
    return result.embeddings[0]
