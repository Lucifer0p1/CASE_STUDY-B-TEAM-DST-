import os
import sys

import pandas as pd
import yaml


def load_config(path="config.yaml"):
    with open(path) as f:
        cfg = yaml.safe_load(f)
    return cfg


def load_bengaluru_hourly(cfg):
    stations_file = cfg["data"]["stations_csv"]
    hourly_file = cfg["data"]["station_hour_csv"]

    for f in [stations_file, hourly_file]:
        if not os.path.exists(f):
            sys.exit("Can't find " + f + " - download it from Kaggle and check config.yaml")

    stations = pd.read_csv(stations_file)
    stations = stations[stations["City"] == cfg["city"]]
    station_ids = stations["StationId"].tolist()

    # station_hour.csv is huge so read it in chunks and only keep bengaluru rows
    keep_cols = ["StationId", "Datetime"] + cfg["pollutants"]
    parts = []
    for chunk in pd.read_csv(hourly_file, chunksize=500000):
        chunk = chunk[chunk["StationId"].isin(station_ids)]
        cols = [c for c in keep_cols if c in chunk.columns]
        parts.append(chunk[cols])

    hourly = pd.concat(parts, ignore_index=True)
    hourly["Datetime"] = pd.to_datetime(hourly["Datetime"])

    print("Stations:", len(stations))
    print("Hourly rows:", len(hourly))
    return hourly, stations


def load_calendar(cfg):
    cal = pd.read_csv(cfg["data"]["festival_calendar_csv"])
    cal["date"] = pd.to_datetime(cal["date"])
    return cal


def load_survey(cfg):
    path = cfg["survey"]["survey_responses_csv"]

    if not path.startswith("http") and not os.path.exists(path):
        print("Survey file not found, skipping survey charts")
        return None

    try:
        survey = pd.read_csv(path)
    except Exception as e:
        print("Couldn't load the survey sheet:", e)
        print("Skipping survey charts")
        return None

    print("Survey responses:", len(survey))
    return survey
