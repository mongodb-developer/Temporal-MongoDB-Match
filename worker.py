import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

import config
from workflows.ingest_trial import IngestTrialWorkflow
from workflows.match_patient import MatchPatientWorkflow

from activities.extract_ehr import extract_ehr
from activities.embed_patient_query import embed_patient_query
from activities.search_clinical_trials import search_clinical_trials
from activities.check_drug_interactions import check_drug_interactions
from activities.generate_summary import generate_summary
from activities.persist_match import persist_match
from activities.ingest_trial import (
    load_raw_trial,
    chunk_trial,
    embed_trial_chunks,
    upsert_trial,
)

async def main() -> None:
    client = await Client.connect(
        config.TEMPORAL_ADDRESS,
        namespace=config.TEMPORAL_NAMESPACE,
    )

    worker = Worker(
        client,
        task_queue=config.TEMPORAL_TASK_QUEUE,
        workflows=[IngestTrialWorkflow, MatchPatientWorkflow],
        activities=[
            extract_ehr,
            embed_patient_query,
            search_clinical_trials,
            check_drug_interactions,
            generate_summary,
            persist_match,
            load_raw_trial,
            chunk_trial,
            embed_trial_chunks,
            upsert_trial,
        ],
    )

    print(f"Polling Temporal task queue: {config.TEMPORAL_TASK_QUEUE}")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
