"""Reading the input files: config, CPCB data, festival calendar and survey."""

import os
import sys

import pandas as pd
import yaml


def load_config(path="config.yaml"):
    """Read config.yaml into a plain Python dictionary."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _require_file(path, what):
    """Stop with a friendly message if an input file is missing."""
    if not os.path.exists(path):
        sys.exit(f"ERROR: {what} not found at '{path}'. "
                 f"Download it and/or fix the path in config.yaml.")


def load_bengaluru_hourly(cfg):
    """Return (hourly data for the city's stations, station table for the city)."""
    stations_path = cfg["data"]["stations_csv"]
    hourly_path = cfg["data"]["station_hour_csv"]
    _require_file(stations_path, "stations.csv")
    _require_file(hourly_path, "station_hour.csv")

    stations = pd.read_csv(stations_path)
    city_stations = stations[stations["City"] == cfg["city"]].copy()
    station_ids = set(city_stations["StationId"])
    print(f"Found {len(station_ids)} stations in {cfg['city']}")

    # station_hour.csv is big, so read it in chunks and keep only our stations
    wanted_cols = ["StationId", "Datetime"] + cfg["pollutants"]
    pieces = []
    for chunk in pd.read_csv(hourly_path, chunksize=500_000):
        chunk = chunk[chunk["StationId"].isin(station_ids)]
        pieces.append(chunk[[c for c in wanted_cols if c in chunk.columns]])
    hourly = pd.concat(pieces, ignore_index=True)
    hourly["Datetime"] = pd.to_datetime(hourly["Datetime"])
    print(f"Loaded {len(hourly):,} hourly rows for {cfg['city']}")
    return hourly, city_stations


def load_calendar(cfg):
    """Read the festival calendar (columns: date, festival)."""
    path = cfg["data"]["festival_calendar_csv"]
    _require_file(path, "festival_calendar.csv")
    calendar = pd.read_csv(path)
    calendar["date"] = pd.to_datetime(calendar["date"])
    return calendar


def load_survey(cfg):
    """Read survey responses from a local CSV or a Google Sheets CSV link.

    Returns None (and the survey charts are skipped) if no file is set up yet.
    """
    source = str(cfg["survey"]["survey_responses_csv"])
    is_link = source.startswith("http")
    if "<" in source or (not is_link and not os.path.exists(source)):
        print(f"Survey responses not found ('{source}') - skipping survey charts.")
        return None
    try:
        survey = pd.read_csv(source)
    except Exception as err:  # e.g. no internet, sheet not shared
        print(f"Could not read survey responses: {err} - skipping survey charts.")
        return None
    print(f"Loaded {len(survey)} survey responses")
    return survey
