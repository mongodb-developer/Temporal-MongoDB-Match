import asyncio
import streamlit as st

from database import get_db
from client.start_match import start
from client.approve_match import send_decision

st.set_page_config(
    page_title="Durable Trial Match",
    page_icon="🧬",
    layout="wide",
)

from pathlib import Path

ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets"

st.image(
    str(ASSET_ROOT / "banner.svg"),
    use_container_width=True,
)

st.warning(
    "Synthetic technical demo only — not for diagnosis, treatment, or real clinical decisions."
)

db = get_db()
patients = list(db.patients.find().sort("_id", 1))

match_tab, review_tab = st.tabs(["🔎 Match Patient", "✅ Physician Review"])

with match_tab:
    if not patients:
        st.info("Run `python scripts/seed_data.py` first.")
    else:
        patient_ids = [p["_id"] for p in patients]
        selected = st.selectbox("Synthetic patient", patient_ids)
        radius = st.slider("Search radius (miles)", 10, 500, 50, 10)

        patient = next(p for p in patients if p["_id"] == selected)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Age", patient["age"])
        c2.metric("Stage", patient["stage"])
        c3.metric("Diagnosis", patient["diagnosis"])
        c4.metric("Radius", f"{radius} mi")

        st.json(patient)

        if st.button("Start Durable Match", type="primary"):
            workflow_id = asyncio.run(start(selected, radius))
            st.success(f"Started Temporal workflow: {workflow_id}")

    st.subheader("Recent matches")
    matches = list(db.matches.find().sort("updatedAt", -1).limit(10))
    for match in matches:
        with st.expander(
            f"{match.get('status', 'UNKNOWN')} — "
            f"{match.get('patientId')} — {match.get('workflowId')}"
        ):
            st.write(match.get("summary", "No summary yet."))
            candidates = match.get("candidateTrials", [])
            if candidates:
                st.dataframe(
                    [
                        {
                            "Trial": c["trialId"],
                            "Score": round(c.get("score", 0), 3),
                            "Miles": c.get("distanceMiles"),
                            "Facility": c.get("facility"),
                        }
                        for c in candidates
                    ],
                    use_container_width=True,
                )

with review_tab:
    waiting = list(
        db.matches.find(
            {"status": "AWAITING_PHYSICIAN_APPROVAL"}
        ).sort("updatedAt", -1)
    )

    if not waiting:
        st.info("No matches are currently waiting for approval.")
    else:
        choice = st.selectbox(
            "Waiting workflow",
            [m["workflowId"] for m in waiting],
        )
        match = next(m for m in waiting if m["workflowId"] == choice)

        st.write(match.get("summary"))
        reviewer = st.text_input("Reviewer", value="Dr. Demo")

        c1, c2 = st.columns(2)

        if c1.button("Approve", type="primary"):
            asyncio.run(send_decision(choice, "approve", reviewer))
            st.success("Approval Signal sent to Temporal.")

        if c2.button("Reject"):
            asyncio.run(send_decision(choice, "reject", reviewer))
            st.success("Rejection Signal sent to Temporal.")
