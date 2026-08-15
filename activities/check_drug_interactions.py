import time
from temporalio import activity
import config

@activity.defn(name="check_drug_interactions")
def check_drug_interactions(payload: dict) -> dict:
    time.sleep(config.DEMO_DRUG_CHECK_DELAY_SECONDS)

    # Temporal Activity attempt numbers survive retry/restart semantics.
    if config.DEMO_FAIL_DRUG_CHECK_ONCE and activity.info().attempt == 1:
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
