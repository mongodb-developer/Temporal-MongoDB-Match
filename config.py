from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    mongodb_uri: str = os.getenv("MONGODB_URI", "")
    mongodb_db: str = os.getenv("MONGODB_DB", "durable_trial_match")
    voyage_api_key: str = os.getenv("VOYAGE_API_KEY", "")
    voyage_model: str = os.getenv("VOYAGE_MODEL", "voyage-4")
    voyage_dimensions: int = int(os.getenv("VOYAGE_DIMENSIONS", "1024"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    temporal_address: str = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    temporal_namespace: str = os.getenv("TEMPORAL_NAMESPACE", "default")
    temporal_task_queue: str = os.getenv("TEMPORAL_TASK_QUEUE", "durable-trial-match")
    demo_fail_drug_check_once: bool = os.getenv("DEMO_FAIL_DRUG_CHECK_ONCE", "true").lower() == "true"
    demo_drug_check_delay_seconds: int = int(os.getenv("DEMO_DRUG_CHECK_DELAY_SECONDS", "4"))

settings = Settings()
