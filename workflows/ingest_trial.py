from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=10),
    maximum_attempts=5,
)

@workflow.defn
class IngestTrialWorkflow:
    @workflow.run
    async def run(self, trial_id: str) -> dict:
        trial = await workflow.execute_activity(
            "load_raw_trial",
            trial_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RETRY,
        )

        chunks = await workflow.execute_activity(
            "chunk_trial",
            trial,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RETRY,
        )

        embedded = await workflow.execute_activity(
            "embed_trial_chunks",
            chunks,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RETRY,
        )

        return await workflow.execute_activity(
            "upsert_trial",
            {"trial": trial, "chunks": embedded},
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=RETRY,
        )
