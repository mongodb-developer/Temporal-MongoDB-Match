from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=15),
    maximum_attempts=5,
)

@workflow.defn
class MatchPatientWorkflow:
    def __init__(self) -> None:
        self.approval = None

    @workflow.signal
    def physician_decision(self, decision: dict) -> None:
        self.approval = decision

    @workflow.run
    async def run(self, payload: dict) -> dict:
        patient_id = payload["patientId"]
        radius_miles = float(payload.get("radiusMiles", 50))
        workflow_id = workflow.info().workflow_id
        match_id = f"match-{workflow_id}"

        patient = await workflow.execute_activity(
            "extract_ehr",
            patient_id,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RETRY,
        )

        query_vector = await workflow.execute_activity(
            "embed_patient_query",
            patient,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RETRY,
        )

        trials = await workflow.execute_activity(
            "search_clinical_trials",
            {
                "patient": patient,
                "queryVector": query_vector,
                "radiusMiles": radius_miles,
            },
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RETRY,
        )

        checked = await workflow.execute_activity(
            "check_drug_interactions",
            {"patient": patient, "trials": trials},
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RETRY,
        )

        summary = await workflow.execute_activity(
            "generate_summary",
            checked,
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=RETRY,
        )

        await workflow.execute_activity(
            "persist_match",
            {
                "matchId": match_id,
                "workflowId": workflow_id,
                "patientId": patient_id,
                "status": "AWAITING_PHYSICIAN_APPROVAL",
                "candidateTrials": checked["trials"],
                "summary": summary,
                "approval": None,
            },
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RETRY,
        )

        await workflow.wait_condition(lambda: self.approval is not None)

        final_status = (
            "APPROVED"
            if self.approval.get("decision") == "APPROVE"
            else "REJECTED"
        )

        await workflow.execute_activity(
            "persist_match",
            {
                "matchId": match_id,
                "workflowId": workflow_id,
                "patientId": patient_id,
                "status": final_status,
                "candidateTrials": checked["trials"],
                "summary": summary,
                "approval": self.approval,
            },
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RETRY,
        )

        return {
            "matchId": match_id,
            "status": final_status,
            "approval": self.approval,
        }
