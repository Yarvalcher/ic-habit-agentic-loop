import asyncio
import os

from bson import json_util
from google.cloud import secretmanager
from motor.motor_asyncio import AsyncIOMotorClient


def get_mongodb_uri():
    client = secretmanager.SecretManagerServiceClient()

    name = "projects/12654003615/secrets/mongodb_url/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


async def seed_collection(db, collection_name, file_path):
    """Loading JSON data in chosen collection with Extended JSON."""
    if not os.path.exists(file_path):
        print(f"⚠️ Файл {file_path} не знайдено. Пропускаємо...")
        return

    try:
        with open(file_path, encoding="utf-8") as f:
            raw_data = f.read()
            data = json_util.loads(raw_data)

        if isinstance(data, list) and len(data) > 0:
            await db[collection_name].delete_many({})
            result = await db[collection_name].insert_many(data)
            print(f"✅ {collection_name}: Loaded {len(result.inserted_ids)} entities.")
    except Exception as e:
        print(f"Collection error {collection_name}: {e}")


async def main():
    print("Starting data migration...")

    try:
        uri = get_mongodb_uri()
        client = AsyncIOMotorClient(uri)

        db = client["habit_os_agent"]

        tasks = [
            seed_collection(
                db, "sessions", r"C:\Users\yaros\Documents\data\habit_os.sessions.json"
            ),
            seed_collection(
                db,
                "sleep_logs",
                r"C:\Users\yaros\Documents\data\habit_os.sleep_logs.json",
            ),
            seed_collection(
                db,
                "body_stats",
                r"C:\Users\yaros\Documents\data\habit_os.body_stats.json",
            ),
            seed_collection(
                db,
                "daily_metrics",
                r"C:\Users\yaros\Documents\data\habit_os.daily_metrics.json",
            ),
        ]

        await asyncio.gather(*tasks)
        print("\nMigration is done!")

    except Exception as e:
        print(f"Error happened: {e}")


if __name__ == "__main__":
    asyncio.run(main())
