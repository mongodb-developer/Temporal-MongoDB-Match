import argparse
import asyncio
from datetime import datetime, timezone

from temporalio.client import Client
from config import settings
from workflows.match_patient import MatchPatientWorkflow

async def send_decision(workflow_id: str, decision: str, reviewer: str) -> None:
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
    )
    handle = client.get_workflow_handle(workflow_id)

    await handle.signal(
        MatchPatientWorkflow.physician_decision,
        {
            "decision": decision.upper(),
            "reviewer": reviewer,
            "reviewedAt": datetime.now(timezone.utc).isoformat(),
        },
    )

async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow_id")
    parser.add_argument("decision", choices=["approve", "reject"])
    parser.add_argument("reviewer")
    args = parser.parse_args()

    await send_decision(args.workflow_id, args.decision, args.reviewer)
    print(f"{args.decision.upper()} signal sent to {args.workflow_id}")

if __name__ == "__main__":
    asyncio.run(main())
