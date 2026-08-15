from datetime import datetime, timezone
from temporalio import activity
import config

@activity.defn(name="persist_match")
def persist_match(payload: dict) -> dict:
    now = datetime.now(timezone.utc)

    config.db.matches.update_one(
        {"_id": payload["matchId"]},
        {
            "$set": {
                "workflowId": payload["workflowId"],
                "patientId": payload["patientId"],
                "status": payload["status"],
                "candidateTrials": payload.get("candidateTrials", []),
                "summary": payload.get("summary"),
                "approval": payload.get("approval"),
                "updatedAt": now,
            },
            "$setOnInsert": {"createdAt": now},
        },
        upsert=True,
    )

    return {"matchId": payload["matchId"], "status": payload["status"]}
