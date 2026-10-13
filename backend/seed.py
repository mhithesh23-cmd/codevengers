"""
seed.py - Seeds sample buyer history data into the Supabase buyer_history table.
"""

import json
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import get_client


def seed_buyer_history():
    """Reads sample_data/buyer_history.json and upserts each record into buyer_history."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "sample_data", "buyer_history.json")

    if not os.path.exists(json_path):
        print(f"Error: {json_path} does not exist.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    client = get_client()
    print(f"Seeding {len(records)} buyer history records into Supabase...")

    for raw_item in records:
        b_name = raw_item.get("buyer_name")
        item = {
            "buyer_name": str(b_name),
            "total_bills": int(raw_item.get("total_bills", 0)),
            "paid_on_time": int(raw_item.get("paid_on_time", 0)),
            "avg_delay_days": int(round(float(raw_item.get("avg_delay_days", 0)))),
        }
        try:
            # Check if record already exists
            existing = client.table("buyer_history").select("*").eq("buyer_name", b_name).execute()
            if existing.data and len(existing.data) > 0:
                client.table("buyer_history").update(item).eq("buyer_name", b_name).execute()
                print(f"Updated buyer: {b_name}")
            else:
                client.table("buyer_history").insert(item).execute()
                print(f"Inserted buyer: {b_name}")
        except Exception as e:
            try:
                client.table("buyer_history").upsert(item).execute()
                print(f"Upserted buyer: {b_name}")
            except Exception as e2:
                print(f"Failed to seed buyer '{b_name}': {e2}")

    print("Seeding complete!")


if __name__ == "__main__":
    seed_buyer_history()
