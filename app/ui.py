from __future__ import annotations

import asyncio
from pathlib import Path

import streamlit as st

import config
from client.approve_match import send_decision
from client.start_match import start


st.set_page_config(
    page_title="Durable Trial Match",
    page_icon="🧬",
    layout="wide",
)

ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets"

st.image(
    str(ASSET_ROOT / "banner.svg"),
    use_container_width=True,
)

st.warning(
    "Synthetic technical demo only — not for diagnosis, treatment, or real clinical decisions."
)

# Atlas connection is hardcoded in config.py.
try:
    config.mongo_client.admin.command("ping")
except Exception as exc:
    st.error("MongoDB Atlas connection failed.")
    st.code(str(exc))
    st.info(
        "Paste the demo Atlas URI into `MONGODB_URI` in `config.py`, "
        "then restart Streamlit."
    )
    st.stop()

with st.sidebar:
    st.header("🍃 MongoDB Atlas")
    st.success("Connected", icon="✅")
    st.caption(f"Database: `{config.MONGODB_DB}`")

    st.divider()

    st.header("⏱️ Temporal")
    st.caption(f"Address: `{config.TEMPORAL_ADDRESS}`")
    st.caption(f"Task queue: `{config.TEMPORAL_TASK_QUEUE}`")

patients = list(config.db.patients.find().sort("_id", 1))

match_tab, review_tab, atlas_tab = st.tabs(
    ["🔎 Match Patient", "✅ Physician Review", "🍃 Atlas State"]
)

with match_tab:
    if not patients:
        st.info(
            "Atlas is connected, but there are no synthetic patients yet. "
            "Run `python scripts/seed_data.py`."
        )
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
            try:
                workflow_id = asyncio.run(start(selected, radius))
            except Exception as exc:
                st.error(
                    "Could not start the Temporal workflow. "
                    f"Check that Temporal is running: {exc}"
                )
            else:
                st.success(f"Started Temporal workflow: {workflow_id}")

    st.subheader("Recent matches")

    matches = list(
        config.db.matches.find()
        .sort("updatedAt", -1)
        .limit(10)
    )

    if not matches:
        st.caption("No match records yet.")

    for match in matches:
        with st.expander(
            f"{match.get('status', 'UNKNOWN')} — "
            f"{match.get('patientId')} — "
            f"{match.get('workflowId')}"
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
        config.db.matches.find(
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

        match = next(
            m for m in waiting
            if m["workflowId"] == choice
        )

        st.write(match.get("summary"))
        reviewer = st.text_input("Reviewer", value="Dr. Demo")

        c1, c2 = st.columns(2)

        if c1.button("Approve", type="primary"):
            try:
                asyncio.run(
                    send_decision(choice, "approve", reviewer)
                )
            except Exception as exc:
                st.error(f"Could not send approval Signal: {exc}")
            else:
                st.success("Approval Signal sent to Temporal.")

        if c2.button("Reject"):
            try:
                asyncio.run(
                    send_decision(choice, "reject", reviewer)
                )
            except Exception as exc:
                st.error(f"Could not send rejection Signal: {exc}")
            else:
                st.success("Rejection Signal sent to Temporal.")

with atlas_tab:
    st.subheader("MongoDB application state")

    collection_names = [
        "patients",
        "raw_trials",
        "trial_chunks",
        "trial_sites",
        "matches",
    ]

    counts = {
        name: config.db[name].count_documents({})
        for name in collection_names
    }

    cols = st.columns(len(counts))
    for col, (name, count) in zip(cols, counts.items()):
        col.metric(name, count)

    st.subheader("Connection")
    st.code(
        f"Database: {config.MONGODB_DB}\n"
        "Atlas ping: OK"
    )

    st.subheader("Collections")
    st.write(sorted(config.db.list_collection_names()))
