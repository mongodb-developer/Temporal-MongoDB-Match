import re
from temporalio import activity

import config
import config

def chunk_text(text: str, max_words: int = 120) -> list[str]:
    words = re.split(r"\s+", text.strip())
    return [
        " ".join(words[i:i + max_words])
        for i in range(0, len(words), max_words)
        if words[i:i + max_words]
    ]

@activity.defn(name="load_raw_trial")
def load_raw_trial(trial_id: str) -> dict:
    trial = config.db.raw_trials.find_one({"_id": trial_id})
    if not trial:
        raise ValueError(f"Raw trial not found: {trial_id}")
    return trial

@activity.defn(name="chunk_trial")
def chunk_trial(trial: dict) -> list[dict]:
    combined = (
        f"{trial['title']}. Diagnosis: {trial['diagnosis']}. "
        f"Eligibility: {trial['eligibilityText']}"
    )

    chunks = []
    for number, text in enumerate(chunk_text(combined)):
        chunks.append(
            {
                "_id": f"{trial['_id']}:{trial['version']}:chunk:{number:03d}",
                "trialId": trial["_id"],
                "version": trial["version"],
                "chunkNumber": number,
                "title": trial["title"],
                "status": trial["status"],
                "minAge": trial["minAge"],
                "maxAge": trial["maxAge"],
                "stage": trial["stage"],
                "text": text,
            }
        )

    return chunks

@activity.defn(name="embed_trial_chunks")
def embed_trial_chunks(chunks: list[dict]) -> list[dict]:
    if not chunks:
        return []
    if not config.VOYAGE_API_KEY:
        raise RuntimeError("VOYAGE_API_KEY is not set")

    client = config.voyage_client
    result = client.embed(
        [chunk["text"] for chunk in chunks],
        model=config.VOYAGE_MODEL,
        input_type="document",
        output_dimension=config.VOYAGE_DIMENSIONS,
    )

    for chunk, vector in zip(chunks, result.embeddings):
        chunk["embedding"] = vector

    return chunks

@activity.defn(name="upsert_trial")
def upsert_trial(payload: dict) -> dict:
    trial = payload["trial"]
    chunks = payload["chunks"]
    db = config.db

    for chunk in chunks:
        db.trial_chunks.update_one(
            {"_id": chunk["_id"]},
            {"$set": chunk},
            upsert=True,
        )

    for site in trial["sites"]:
        db.trial_sites.update_one(
            {"_id": site["_id"]},
            {
                "$set": {
                    "trialId": trial["_id"],
                    "facility": site["facility"],
                    "location": site["location"],
                }
            },
            upsert=True,
        )

    return {
        "trialId": trial["_id"],
        "chunksUpserted": len(chunks),
        "sitesUpserted": len(trial["sites"]),
    }
