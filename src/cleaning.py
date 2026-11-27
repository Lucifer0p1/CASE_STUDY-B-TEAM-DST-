"""Cleaning rules for the CPCB hourly data.

Each rule records how many rows (and individual values) it changed,
so main.py can print a cleaning summary.
"""

import pandas as pd


def make_hourly_grid(df):
    """Give every station one row per hour, so missing hours become empty rows.

    This makes "6 hours unchanged" and "gaps of 3 hours" mean real clock hours.
    """
    df = df.drop_duplicates(["StationId", "Datetime"]).sort_values(["StationId", "Datetime"])
    pieces = []
    for station_id, group in df.groupby("StationId"):
        all_hours = pd.date_range(group["Datetime"].min(), group["Datetime"].max(), freq="h")
        group = group.set_index("Datetime").reindex(all_hours)
        group["StationId"] = station_id
        pieces.append(group.rename_axis("Datetime").reset_index())
    return pd.concat(pieces, ignore_index=True)


def flatline_mask(series, min_hours):
    """True where a value repeats unchanged for `min_hours` or more hours in a row."""
    run_id = (series != series.shift()).cumsum()          # new id whenever the value changes
    run_length = series.groupby(run_id).transform("size")
    return series.notna() & (run_length >= min_hours)


def fill_short_gaps(series, max_gap):
    """Linearly fill gaps of `max_gap` hours or less; leave longer gaps empty."""
    missing = series.isna()
    gap_id = (missing != missing.shift()).cumsum()
    gap_length = missing.groupby(gap_id).transform("sum")
    filled = series.interpolate(limit_area="inside")     # only between two real values
    to_fill = missing & (gap_length <= max_gap) & filled.notna()
    return series.where(~to_fill, filled)


def clean_hourly(df, cfg):
    """Apply all cleaning rules. Returns (clean data, summary table)."""
    rules = cfg["cleaning"]
    pollutants = [p for p in cfg["pollutants"] if p in df.columns]
    summary = []

    def record(rule, mask):
        summary.append({"rule": rule,
                        "rows_affected": int(mask.any(axis=1).sum()),
                        "values_affected": int(mask.sum().sum())})

    rows_before = len(df)
    df = make_hourly_grid(df)
    summary.append({"rule": "Missing hours added as empty rows",
                    "rows_affected": len(df) - rows_before, "values_affected": 0})

    # Rule 1: sensor error codes -> missing
    mask = df[pollutants].isin(rules["error_codes"])
    df[pollutants] = df[pollutants].mask(mask)
    record(f"Error codes {rules['error_codes']} set to missing", mask)

    # Rule 2: CO == 0 -> missing
    mask = pd.DataFrame(False, index=df.index, columns=pollutants)
    if rules.get("co_zero_is_missing") and "CO" in pollutants:
        mask["CO"] = df["CO"] == 0
        df.loc[mask["CO"], "CO"] = float("nan")
    record("CO == 0 set to missing", mask)

    # Rule 3: values stuck for N+ hours (per station) -> missing
    n = rules["flatline_hours"]
    mask = pd.DataFrame(False, index=df.index, columns=pollutants)
    for p in pollutants:
        mask[p] = df.groupby("StationId")[p].transform(lambda s: flatline_mask(s, n)).astype(bool)
    df[pollutants] = df[pollutants].mask(mask)
    record(f"Unchanged for {n}+ hours set to missing", mask)

    # Rule 4: fill short gaps with linear interpolation
    gap = rules["max_interpolate_gap_hours"]
    was_missing = df[pollutants].isna()
    for p in pollutants:
        df[p] = df.groupby("StationId")[p].transform(lambda s: fill_short_gaps(s, gap))
    record(f"Gaps of {gap} hours or less filled (interpolated)", was_missing & df[pollutants].notna())

    still_missing = df[pollutants].isna()
    summary.append({"rule": "Values still missing after cleaning (all pollutants)",
                    "rows_affected": int(still_missing.any(axis=1).sum()),
                    "values_affected": int(still_missing.sum().sum())})
    return df, pd.DataFrame(summary)
