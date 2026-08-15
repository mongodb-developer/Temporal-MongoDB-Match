from pymongo import MongoClient
import voyageai

# -------------------------------------------------------------------
# DURABLE TRIAL MATCH — DEMO CONFIG
# -------------------------------------------------------------------
# Paste throwaway demo credentials directly here.
# Do not commit production credentials.

MONGODB_URI = "mongodb+srv://USERNAME:PASSWORD@CLUSTER.mongodb.net/"
MONGODB_DB = "durable_trial_match"

VOYAGE_API_KEY = "PASTE_VOYAGE_API_KEY_HERE"
VOYAGE_MODEL = "voyage-4"
VOYAGE_DIMENSIONS = 1024

OPENAI_API_KEY = ""
OPENAI_MODEL = "gpt-5-mini"

TEMPORAL_ADDRESS = "localhost:7233"
TEMPORAL_NAMESPACE = "default"
TEMPORAL_TASK_QUEUE = "durable-trial-match"

DEMO_FAIL_DRUG_CHECK_ONCE = True
DEMO_DRUG_CHECK_DELAY_SECONDS = 4

# -------------------------------------------------------------------
# Shared demo clients
# -------------------------------------------------------------------

mongo_client = MongoClient(
    MONGODB_URI,
    appname="durable-trial-match",
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
)

db = mongo_client[MONGODB_DB]

voyage_client = voyageai.Client(
    api_key=VOYAGE_API_KEY
)
