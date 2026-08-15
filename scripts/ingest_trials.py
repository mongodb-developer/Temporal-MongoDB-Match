import asyncio

from temporalio.client import Client
from config import settings
from database import get_db
from workflows.ingest_trial import IngestTrialWorkflow

async def main() -> None:
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
    )

    trial_ids = [
        doc["_id"]
        for doc in get_db().raw_trials.find({}, {"_id": 1}).sort("_id", 1)
    ]

    handles = []
    for trial_id in trial_ids:
        handle = await client.start_workflow(
            IngestTrialWorkflow.run,
            trial_id,
            id=f"ingest-{trial_id}",
            task_queue=settings.temporal_task_queue,
        )
        handles.append((trial_id, handle))
        print(f"Started ingest-{trial_id}")

    for trial_id, handle in handles:
        print(trial_id, await handle.result())

if __name__ == "__main__":
    asyncio.run(main())
