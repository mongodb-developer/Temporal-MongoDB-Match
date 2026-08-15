import time
from temporalio import activity
from config import settings

@activity.defn(name="check_drug_interactions")
def check_drug_interactions(payload: dict) -> dict:
    time.sleep(settings.demo_drug_check_delay_seconds)

    # Temporal Activity attempt numbers survive retry/restart semantics.
    if settings.demo_fail_drug_check_once and activity.info().attempt == 1:
        raise RuntimeError(
            "DEMO: simulated drug-interaction service timeout on attempt 1"
        )

    for trial in payload["trials"]:
        trial["interactionCheck"] = {
            "status": "CLEAR",
            "note": "Synthetic demo only — no real pharmacology data used.",
            "medicationsReviewed": payload["patient"]["medications"],
        }

    return payload
