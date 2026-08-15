import argparse
import asyncio
from datetime import datetime, timezone

from temporalio.client import Client
import config
from workflows.match_patient import MatchPatientWorkflow

async def send_decision(workflow_id: str, decision: str, reviewer: str) -> None:
    client = await Client.connect(
        config.TEMPORAL_ADDRESS,
        namespace=config.TEMPORAL_NAMESPACE,
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
