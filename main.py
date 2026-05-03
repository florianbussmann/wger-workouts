from collections import defaultdict
import requests
import json


import os
from dotenv import load_dotenv

load_dotenv()


def read_env(env, default=None):
    return os.getenv(env, default)


API_KEY = read_env("API_KEY")
BASE_URL = read_env("BASE_URL", "https://wger.de/api/v2")
PREFERRED_LANG = int(read_env("PREFERRED_LANG", 2))
PAGE_LIMIT = int(read_env("PAGE_LIMIT", 50))


headers = {"Authorization": f"Token {API_KEY}", "Accept": "application/json"}


def extract_name(exercise_info):
    for t in exercise_info.get("translations", []):
        if t["language"] == PREFERRED_LANG:
            return t["name"]

    # fallback to first available language
    if exercise_info.get("translations"):
        return exercise_info["translations"][0]["name"]

    return None


def export_workout(workout, filename="last_workout.json"):
    with open(filename, "w") as f:
        json.dump(workout, f, indent=4, default=str)
    print(f"Exported to {filename}")


def fetch(endpoint, params=None):
    r = requests.get(f"{BASE_URL}/{endpoint}", headers=headers, params=params or {})
    r.raise_for_status()
    return r.json()


def get_last_session():
    data = fetch("workoutsession", {"limit": 1, "ordering": "-date"})
    return data["results"][0] if data["results"] else None


def get_logs(session_id):
    return get_paginated(endpoint="workoutlog", params={"session": session_id, "limit": PAGE_LIMIT})

def get_paginated(endpoint, params={"limit": PAGE_LIMIT}):
    url = f"{BASE_URL}/{endpoint}/"

    all_results = []

    while url:
        data = fetch(endpoint, params)

        all_results.extend(data["results"])

        # after first request, params must NOT be reused
        url = data.get("next")
        if url:
            url = url.replace("http:", "https:")
        params = None  # important: only send params on first call

    return all_results

def get_slot_map():
    return {s["id"]: s for s in get_paginated("slot-entry")}


def get_exercise_name(exercise_id, cache={}):
    if exercise_id in cache:
        return cache[exercise_id]

    data = fetch(f"exerciseinfo/{exercise_id}")

    name = extract_name(data) or f"Exercise {exercise_id}"
    cache[exercise_id] = name
    return name


def build_workout(session):
    logs = get_logs(session["id"])

    result = {"date": session.get("date"), "notes": session.get("notes"), "sets": []}

    for log in logs:
        result["sets"].append(
            {
                "exercise": get_exercise_name(log["exercise"]),
                "reps": float(log["repetitions"]) if log.get("repetitions") else None,
                "slot_entry": int(log["slot_entry"]) if log.get("slot_entry") else None,
                "weight": float(log["weight"]) if log.get("weight") else None,
            }
        )

    return result


def format_workout(data):
    logs = data["sets"]

    slot_map = get_slot_map()
    # group by slot_entry
    slots = defaultdict(list)
    for log in logs:
        slots[log["slot_entry"]].append(log)

    lines = []
    lines.append("🏋️ Workout —")

    slot_items = defaultdict(list)

    for s in slot_map.values():
        slot_items[s["slot"]].append(s)

    slot_overview = {
        slot_id: {
            "exercises": len(items),
            "is_superset": len(items) > 1,
            "slots": items
        }
        for slot_id, items in slot_items.items()
    }

    last_slot = None

    for _, (slot_id, entries) in enumerate(sorted(slots.items()), start=1):
        slot_info = slot_map.get(slot_id, {})
        if last_slot != slot_info.get("slot"):
            lines.append("")
            last_slot = slot_info.get("slot")
            if slot_overview.get(last_slot).get("is_superset"):
                lines.append(f"Superset {last_slot}:")

        # all entries in a slot belong to ONE exercise
        exercise = entries[0]["exercise"]
        lines.append(f"{exercise}")

        for e in entries:
            reps = int(float(e.get("reps") or 0))
            weight = float(e.get("weight") or 0)

            if weight > 0:
                lines.append(f"- {reps} reps @ {int(weight)} kg")
            else:
                lines.append(f"- {reps} reps")

    return "\n".join(lines)


def main():
    print("Hello from wger-workouts!")

    session = get_last_session()

    if not session:
        print("No sessions found")
        return

    workout = build_workout(session)
    export_workout(workout)

    print(format_workout(workout))


if __name__ == "__main__":
    main()
