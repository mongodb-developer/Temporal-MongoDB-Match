##A small MongoDB Atlas + Temporal MVP that demonstrates production-oriented RAG and agent workflows using a **synthetic clinical-trial matching** scenario.

Most AI demos prove that an LLM can answer a question. This project proves three harder things:

1. **MongoDB can combine strict operational filters with semantic retrieval.**
2. **Temporal can recover an interrupted multi-step AI workflow without re-running completed expensive steps.**
3. **A long-running workflow can safely pause for human approval while MongoDB remains the operational source of truth for the UI.**

The division of responsibility is intentionally simple:

- **MongoDB Atlas**: patient/trial operational data, GeoJSON, structured filters, vector search, workflow-facing application state, and Change Streams.
- **Voyage AI**: embeddings for trial eligibility text and patient-match queries.
- **Temporal**: durable ingestion, retries, crash recovery, workflow state, and human-in-the-loop waiting.
- **LLM**: extraction and final grounded summary generation.

---

## The three demo moments

### 1. Hybrid metadata pre-filtering + vector search

A user enters a synthetic patient profile containing:

- age
- cancer stage
- symptoms/clinical notes
- current medications
- home location as GeoJSON
- desired search radius

MongoDB performs the match in two native steps.

#### Step A: GeoJSON proximity lookup

Trial sites are stored as GeoJSON `Point` values with a `2dsphere` index.

```javascript
db.trial_sites.createIndex({ location: "2dsphere" })
```

Example site:

```json
{
  "_id": "site-chi-001",
  "trialId": "NCT-DEMO-1001",
  "facility": "Chicago Research Center",
  "location": {
    "type": "Point",
    "coordinates": [-87.6298, 41.8781]
  }
}
```

Resolve eligible trial IDs within the requested radius:

```javascript
db.trial_sites.aggregate([
  {
    "$geoNear": {
      "near": {
        "type": "Point",
        "coordinates": [-87.6298, 41.8781]
      },
      "distanceField": "distanceMeters",
      "maxDistance": 80467.2,
      "spherical": true
    }
  },
  {
    "$group": {
      "_id": "$trialId",
      "nearestDistanceMeters": { "$min": "$distanceMeters" }
    }
  }
])
```

`80467.2` meters is 50 miles.

#### Step B: Vector Search with strict metadata pre-filtering

The resulting `trialId` values are fed into the `$vectorSearch.filter` together with strict patient constraints.

Conceptually:

```javascript
[
  {
    "$vectorSearch": {
      "index": "trial_match_vector",
      "path": "eligibilityEmbedding",
      "queryVector": "<patient-query-embedding>",
      "numCandidates": 200,
      "limit": 20,
      "filter": {
        "$and": [
          { "trialId": { "$in": ["NCT-DEMO-1001", "NCT-DEMO-1008"] } },
          { "minAge": { "$lte": 54 } },
          { "maxAge": { "$gte": 54 } },
          { "stage": "III" },
          { "status": "RECRUITING" }
        ]
      }
    }
  }
]
```

This demonstrates **semantic similarity only across trials that already satisfy hard operational constraints**.

The geographic search is intentionally a separate MongoDB query because `$vectorSearch` must be the first stage in the aggregation pipeline where it appears.

---

### 2. The "Token-Saver" crash recovery

The core matching workflow contains five visible steps:

```text
1. Extract synthetic EHR facts
2. Embed the normalized patient query
3. Search eligible clinical trials
4. Check drug interactions
5. Generate grounded summary
```

During the demo, force an error or kill the worker while step 4 is executing.

Expected Temporal history:

```text
✓ Extract EHR
✓ Embed patient query
✓ Search trials
✗ Check drug interactions     <-- injected failure
```

Restart the worker.

```text
✓ Extract EHR                 <-- recovered from workflow history
✓ Embed patient query         <-- recovered from workflow history
✓ Search trials               <-- recovered from workflow history
✓ Check drug interactions     <-- resumes/retries here
✓ Generate summary
```

Important implementation detail: Temporal **replays workflow history to reconstruct state**, but successfully completed Activities are not re-executed. That is why the prior LLM call, embedding request, and MongoDB search do not need to be paid for or performed again.

For the demo, the drug-interaction activity can use a deterministic local mock service so no external clinical API is required.

---

### 3. Async human-in-the-loop approval

After the AI produces candidate trial matches, the workflow updates MongoDB:

```json
{
  "_id": "match-8f2c",
  "patientId": "patient-demo-001",
  "workflowId": "trial-match-patient-demo-001-v7",
  "status": "AWAITING_PHYSICIAN_APPROVAL",
  "recommendedTrialIds": [
    "NCT-DEMO-1001",
    "NCT-DEMO-1008"
  ],
  "approval": null
}
```

The Temporal workflow then waits for a Signal:

```python
await workflow.wait_condition(lambda: self.approval is not None)
```

The UI watches the MongoDB `matches` collection using a Change Stream.

When the attending-review simulator approves the result:

1. The application sends a Temporal Signal.
2. The workflow records the approval.
3. The workflow updates the MongoDB operational record.
4. The MongoDB Change Stream pushes the updated state to the UI.

The workflow can remain waiting without a worker thread sitting blocked for the duration.

---

# Architecture

```text
                         ┌──────────────────────┐
                         │      Streamlit       │
                         │ Patient / Trial UI   │
                         └──────────┬───────────┘
                                    │
                   start workflow / signal approval
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       Temporal       │
                         │                      │
                         │ IngestTrialWorkflow  │
                         │ MatchPatientWorkflow │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼──────────────────────┐
              │                     │                      │
              ▼                     ▼                      ▼
      ┌───────────────┐     ┌───────────────┐      ┌──────────────┐
      │   Voyage AI   │     │ MongoDB Atlas │      │      LLM     │
      │  Embeddings   │     │               │      │ extraction + │
      └───────────────┘     │ patients      │      │ summary      │
                            │ trials        │      └──────────────┘
                            │ trial_sites   │
                            │ matches       │
                            │               │
                            │ 2dsphere      │
                            │ Vector Search │
                            │ Change Stream │
                            └───────────────┘
```

---

# MongoDB collections

## `patients`

Synthetic operational patient data.

```json
{
  "_id": "patient-demo-001",
  "age": 54,
  "stage": "III",
  "diagnosis": "synthetic NSCLC",
  "symptoms": ["fatigue", "persistent cough"],
  "medications": ["demo-drug-a"],
  "location": {
    "type": "Point",
    "coordinates": [-87.6298, 41.8781]
  }
}
```

## `trials`

One document per synthetic trial.

```json
{
  "_id": "NCT-DEMO-1001",
  "trialId": "NCT-DEMO-1001",
  "title": "Synthetic Stage III NSCLC Trial",
  "status": "RECRUITING",
  "minAge": 18,
  "maxAge": 75,
  "stage": "III",
  "eligibilityText": "Adults with synthetic stage III NSCLC...",
  "eligibilityEmbedding": [0.012, -0.034, 0.055]
}
```

## `trial_sites`

One document per site so a trial can have multiple recruiting locations.

```json
{
  "_id": "site-chi-001",
  "trialId": "NCT-DEMO-1001",
  "facility": "Chicago Research Center",
  "location": {
    "type": "Point",
    "coordinates": [-87.6298, 41.8781]
  }
}
```

Indexes:

```javascript
db.trial_sites.createIndex({ location: "2dsphere" })
db.trial_sites.createIndex({ trialId: 1 })
```

## `matches`

Operational state for the UI and approval workflow.

```json
{
  "_id": "match-8f2c",
  "patientId": "patient-demo-001",
  "workflowId": "trial-match-patient-demo-001-v7",
  "status": "AWAITING_PHYSICIAN_APPROVAL",
  "candidateTrials": [],
  "approval": null,
  "createdAt": "2026-08-15T00:00:00Z",
  "updatedAt": "2026-08-15T00:00:00Z"
}
```

---

# Durable ingestion

Trial ingestion is also a Temporal workflow:

```text
Raw synthetic trial JSON
        ↓
Temporal IngestTrialWorkflow
        ↓
Normalize metadata
        ↓
Chunk long eligibility text
        ↓
Generate Voyage embeddings
        ↓
Idempotent Atlas upsert
        ↓
Searchable
```

Use a deterministic workflow ID:

```text
ingest-trial-NCT-DEMO-1001-v3
```

and idempotent MongoDB upserts:

```python
collection.update_one(
    {"trialId": trial["trialId"], "chunkId": chunk["chunkId"]},
    {"$set": chunk},
    upsert=True,
)
```

Repeated ingestion therefore updates the existing logical chunk instead of generating duplicates.

---

# Suggested project structure

```text
durable-trial-match/
├── README.md
├── docker-compose.yml
├── .env.example
├── requirements.txt
│
├── app/
│   ├── ui.py
│   ├── approval.py
│   └── change_stream.py
│
├── workflows/
│   ├── ingest_trial.py
│   └── match_patient.py
│
├── activities/
│   ├── extract_ehr.py
│   ├── embed_query.py
│   ├── geo_filter.py
│   ├── vector_search.py
│   ├── drug_interactions.py
│   ├── generate_summary.py
│   └── persist_state.py
│
├── mongodb/
│   ├── indexes/
│   │   └── trial_match_vector.json
│   ├── repositories.py
│   └── change_streams.py
│
├── data/
│   ├── synthetic_patients.json
│   ├── synthetic_trials.json
│   └── synthetic_trial_sites.json
│
├── scripts/
│   ├── seed.py
│   ├── create_indexes.py
│   └── inject_failure.py
│
└── tests/
    ├── test_ingest_idempotency.py
    ├── test_geo_filter.py
    └── test_workflow_recovery.py
```

---

# Recommended demo flow

### Scene 1 — Show the data

Open Atlas and show:

- `patients`
- `trials`
- `trial_sites`
- GeoJSON coordinates
- Vector Search index
- `matches`

### Scene 2 — Start a patient match

Use:

```text
Age:      54
Stage:    III
Location: Chicago
Radius:   50 miles

Symptoms:
persistent cough, fatigue, synthetic NSCLC
```

Show the application resolving nearby sites with GeoJSON, then Vector Search operating only on trials that satisfy the strict metadata constraints.

### Scene 3 — Break it

Start the five-step workflow.

When `Check Drug Interactions` begins:

```bash
docker stop temporal-worker
```

or use the built-in failure-injection flag.

Show Temporal history proving steps 1-3 completed.

Restart the worker.

The workflow continues without re-running the completed expensive Activities.

### Scene 4 — Human approval

The result lands in MongoDB with:

```text
AWAITING_PHYSICIAN_APPROVAL
```

Leave it there for a moment.

Click:

```text
Approve Match
```

The button sends a Temporal Signal.

Temporal wakes the workflow and updates the record to:

```text
APPROVED
```

The UI changes immediately from the MongoDB Change Stream.

---

# MVP success criteria

The demo is successful when it proves all of the following:

- GeoJSON radius filtering is executed using MongoDB geospatial capabilities.
- Strict structured metadata filters reduce the eligible trial set.
- Vector Search ranks semantically relevant trials from only that eligible set.
- Trial ingestion is idempotent.
- A workflow failure after step 3 does not re-execute completed expensive Activities.
- Workflow execution history remains visible in Temporal.
- A workflow can wait asynchronously for approval.
- Approval is delivered through a Temporal Signal.
- MongoDB stores the current operational state of the match.
- A Change Stream updates the UI when match state changes.

---

# MVP boundaries

Keep version one intentionally small:

- synthetic data only
- 25-50 trials
- 50-100 trial sites
- 3-5 sample patients
- one Atlas cluster
- one Temporal worker
- one Streamlit app
- one embedding model
- one LLM
- mocked drug-interaction service
- no Kafka
- no Kubernetes
- no authentication system
- no production medical APIs

The point is not to build a clinical application.

The point is to make **MongoDB + Temporal durability visually undeniable in ten minutes**.
