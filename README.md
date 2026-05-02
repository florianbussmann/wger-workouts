# wger-workouts

Parses workouts from wger instance e.g. to add information to Strava.

Requires API_KEY from https://wger.de/de/user/api-key to be stored in `.env`. Another wger instance can be specified using variable `BASE_URL=https://wger.example.co/api/v2`.

```shell
cp .env_example .env
nano .env
uv run main.py
```
