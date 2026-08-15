import config


def main() -> None:
    config.mongo_client.admin.command("ping")

    print("Atlas connection: OK")
    print(f"Database: {config.MONGODB_DB}")
    print("Collections:")

    for name in sorted(config.db.list_collection_names()):
        print(f"  - {name}")


if __name__ == "__main__":
    main()
