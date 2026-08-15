import argparse
import asyncio
import uuid

from temporalio.client import Client
import config
from workflows.match_patient import MatchPatientWorkflow

async def start(patient_id: str, radius: float) -> str:
    client = await Client.connect(
        config.TEMPORAL_ADDRESS,
        namespace=config.TEMPORAL_NAMESPACE,
    )

    workflow_id = f"trial-match-{patient_id}-{uuid.uuid4().hex[:8]}"

    await client.start_workflow(
        MatchPatientWorkflow.run,
        {"patientId": patient_id, "radiusMiles": radius},
        id=workflow_id,
        task_queue=config.TEMPORAL_TASK_QUEUE,
    )

    return workflow_id

async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("patient_id")
    parser.add_argument("--radius", type=float, default=50)
    args = parser.parse_args()

    workflow_id = await start(args.patient_id, args.radius)
    print(workflow_id)

if __name__ == "__main__":
    asyncio.run(main())
