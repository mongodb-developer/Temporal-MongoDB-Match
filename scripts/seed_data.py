import json
from pathlib import Path
from database import get_db

ROOT = Path(__file__).resolve().parents[1]

def load_json(name: str):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))

def main() -> None:
    db = get_db()
    patients = load_json("synthetic_patients.json")
    trials = load_json("synthetic_trials.json")

    for patient in patients:
        db.patients.update_one(
            {"_id": patient["_id"]},
            {"$set": patient},
            upsert=True,
        )

    for trial in trials:
        db.raw_trials.update_one(
            {"_id": trial["_id"]},
            {"$set": trial},
            upsert=True,
        )

    print(f"Seeded {len(patients)} synthetic patients")
    print(f"Seeded {len(trials)} synthetic raw trials")

if __name__ == "__main__":
    main()
