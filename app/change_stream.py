import config

def main() -> None:
    print("Watching MongoDB match state with Change Streams...")
    print("Ctrl+C to stop.\n")

    pipeline = [
        {
            "$match": {
                "operationType": {"$in": ["insert", "update", "replace"]}
            }
        }
    ]

    with config.db.matches.watch(
        pipeline,
        full_document="updateLookup",
    ) as stream:
        for change in stream:
            match = change.get("fullDocument")
            if match:
                print(
                    f"{match['_id']} -> {match.get('status')} "
                    f"(workflow={match.get('workflowId')})"
                )

if __name__ == "__main__":
    main()
