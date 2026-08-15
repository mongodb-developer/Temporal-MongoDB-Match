import argparse
import asyncio
import uuid

from temporalio.client import Client
from config import settings
from workflows.match_patient import MatchPatientWorkflow

async def start(patient_id: str, radius: float) -> str:
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
    )

    workflow_id = f"trial-match-{patient_id}-{uuid.uuid4().hex[:8]}"

    await client.start_workflow(
        MatchPatientWorkflow.run,
        {"patientId": patient_id, "radiusMiles": radius},
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
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
