import pandas as pd


def fill_missing_hours(df):
    # make sure every station has a row for every hour
    # (otherwise "6 hours in a row" and "3 hour gap" don't really mean anything)
    df = df.drop_duplicates(subset=["StationId", "Datetime"])
    out = []
    for station, g in df.groupby("StationId"):
        all_hours = pd.date_range(g["Datetime"].min(), g["Datetime"].max(), freq="h")
        g = g.set_index("Datetime").reindex(all_hours)
        g["StationId"] = station
        g.index.name = "Datetime"
        out.append(g.reset_index())
    return pd.concat(out, ignore_index=True)


def find_stuck_values(s, hours):
    # each time the value changes we start a new "run"
    run_id = (s != s.shift()).cumsum()
    run_len = s.groupby(run_id).transform("size")
    return s.notna() & (run_len >= hours)


def interpolate_short_gaps(s, max_gap):
    is_nan = s.isna()
    gap_id = (is_nan != is_nan.shift()).cumsum()
    gap_len = is_nan.groupby(gap_id).transform("sum")

    interpolated = s.interpolate(limit_area="inside")
    short_gap = is_nan & (gap_len <= max_gap)
    s = s.copy()
    s[short_gap] = interpolated[short_gap]
    return s


def clean_hourly(df, cfg):
    rules = cfg["cleaning"]
    cols = [c for c in cfg["pollutants"] if c in df.columns]
    log = []

    n_before = len(df)
    df = fill_missing_hours(df)
    log.append(["Missing hours added as empty rows", len(df) - n_before, 0])

    # 1) error codes
    bad = df[cols].isin(rules["error_codes"])
    df[cols] = df[cols].mask(bad)
    log.append(["Error codes set to missing", bad.any(axis=1).sum(), bad.sum().sum()])

    # 2) CO = 0 is not a real reading
    co_zero = df["CO"] == 0
    df.loc[co_zero, "CO"] = None
    log.append(["CO == 0 set to missing", co_zero.sum(), co_zero.sum()])

    # 3) sensor stuck on the same value
    hours = rules["flatline_hours"]
    stuck = pd.DataFrame(index=df.index)
    for c in cols:
        stuck[c] = df.groupby("StationId")[c].transform(lambda s: find_stuck_values(s, hours))
    stuck = stuck.astype(bool)
    df[cols] = df[cols].mask(stuck)
    log.append([f"Unchanged for {hours}+ hours set to missing", stuck.any(axis=1).sum(), stuck.sum().sum()])

    # 4) fill small gaps
    max_gap = rules["max_interpolate_gap_hours"]
    was_nan = df[cols].isna()
    for c in cols:
        df[c] = df.groupby("StationId")[c].transform(lambda s: interpolate_short_gaps(s, max_gap))
    filled = was_nan & df[cols].notna()
    log.append([f"Gaps of {max_gap} hours or less interpolated", filled.any(axis=1).sum(), filled.sum().sum()])

    summary = pd.DataFrame(log, columns=["rule", "rows", "values"])
    return df, summary
