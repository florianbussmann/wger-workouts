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
    return fetch("workoutlog", {"session": session_id})["results"]


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
                "weight": float(log["weight"]) if log.get("weight") else None,
            }
        )

    return result


def main():
    print("Hello from wger-workouts!")

    session = get_last_session()

    if not session:
        print("No sessions found")
        return

    workout = build_workout(session)
    export_workout(workout)


if __name__ == "__main__":
    main()
