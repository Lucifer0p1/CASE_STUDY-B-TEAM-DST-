import os
import sys

import pandas as pd
import yaml


def load_config(path="config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_file(path):
    if not os.path.exists(path):
        sys.exit(f"ERROR: file not found: {path} (check config.yaml)")


def load_bengaluru_hourly(cfg):
    check_file(cfg["data"]["stations_csv"])
    check_file(cfg["data"]["station_hour_csv"])

    stations = pd.read_csv(cfg["data"]["stations_csv"])
    stations = stations[stations["City"] == cfg["city"]]
    ids = set(stations["StationId"])

    columns = ["StationId", "Datetime"] + cfg["pollutants"]
    pieces = []
    for chunk in pd.read_csv(cfg["data"]["station_hour_csv"], chunksize=500_000):
        chunk = chunk[chunk["StationId"].isin(ids)]
        pieces.append(chunk[[c for c in columns if c in chunk.columns]])
    hourly = pd.concat(pieces, ignore_index=True)
    hourly["Datetime"] = pd.to_datetime(hourly["Datetime"])

    print(f"{len(stations)} stations, {len(hourly):,} hourly rows")
    return hourly, stations


def load_calendar(cfg):
    check_file(cfg["data"]["festival_calendar_csv"])
    calendar = pd.read_csv(cfg["data"]["festival_calendar_csv"])
    calendar["date"] = pd.to_datetime(calendar["date"])
    return calendar


def load_survey(cfg):
    source = str(cfg["survey"]["survey_responses_csv"])
    if not source.startswith("http") and not os.path.exists(source):
        print(f"No survey file at {source}, skipping survey charts")
        return None
    try:
        return pd.read_csv(source)
    except Exception as error:
        print(f"Could not read survey ({error}), skipping survey charts")
        return None
