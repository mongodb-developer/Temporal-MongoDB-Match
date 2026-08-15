from temporalio import activity
from database import get_db

MILES_TO_METERS = 1609.344

def _nearby_trials(patient: dict, radius_miles: float) -> list[dict]:
    longitude, latitude = patient["location"]["coordinates"]

    pipeline = [
        {
            "$geoNear": {
                "near": {
                    "type": "Point",
                    "coordinates": [longitude, latitude],
                },
                "distanceField": "distanceMeters",
                "maxDistance": radius_miles * MILES_TO_METERS,
                "spherical": True,
            }
        },
        {
            "$group": {
                "_id": "$trialId",
                "nearestDistanceMeters": {"$min": "$distanceMeters"},
                "facility": {"$first": "$facility"},
            }
        },
    ]

    return list(get_db().trial_sites.aggregate(pipeline))

@activity.defn(name="search_clinical_trials")
def search_clinical_trials(payload: dict) -> list[dict]:
    patient = payload["patient"]
    query_vector = payload["queryVector"]
    radius_miles = float(payload.get("radiusMiles", 50))

    nearby = _nearby_trials(patient, radius_miles)
    if not nearby:
        return []

    geo_by_trial = {
        row["_id"]: {
            "distanceMiles": row["nearestDistanceMeters"] / MILES_TO_METERS,
            "facility": row.get("facility"),
        }
        for row in nearby
    }

    nearby_ids = list(geo_by_trial)

    pipeline = [
        {
            "$vectorSearch": {
                "index": "trial_match_vector",
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": 200,
                "limit": 25,
                "filter": {
                    "$and": [
                        {"trialId": {"$in": nearby_ids}},
                        {"minAge": {"$lte": patient["age"]}},
                        {"maxAge": {"$gte": patient["age"]}},
                        {"stage": {"$eq": patient["stage"]}},
                        {"status": {"$eq": "RECRUITING"}},
                    ]
                },
            }
        },
        {
            "$project": {
                "_id": 1,
                "trialId": 1,
                "title": 1,
                "text": 1,
                "stage": 1,
                "minAge": 1,
                "maxAge": 1,
                "status": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    rows = list(get_db().trial_chunks.aggregate(pipeline))

    best_by_trial = {}
    for row in rows:
        trial_id = row["trialId"]
        if trial_id in best_by_trial:
            continue

        geo = geo_by_trial[trial_id]
        row["distanceMiles"] = round(geo["distanceMiles"], 1)
        row["facility"] = geo["facility"]
        best_by_trial[trial_id] = row

    return list(best_by_trial.values())[:10]
