import pandas as pd


def make_hourly_grid(df):
    df = df.drop_duplicates(["StationId", "Datetime"])
    pieces = []
    for station, group in df.groupby("StationId"):
        hours = pd.date_range(group["Datetime"].min(), group["Datetime"].max(), freq="h")
        group = group.set_index("Datetime").reindex(hours)
        group["StationId"] = station
        pieces.append(group.rename_axis("Datetime").reset_index())
    return pd.concat(pieces, ignore_index=True)


def flatline(series, hours):
    run = (series != series.shift()).cumsum()
    run_length = series.groupby(run).transform("size")
    return series.notna() & (run_length >= hours)


def fill_short_gaps(series, max_gap):
    missing = series.isna()
    gap = (missing != missing.shift()).cumsum()
    gap_length = missing.groupby(gap).transform("sum")
    filled = series.interpolate(limit_area="inside")
    return series.where(~(missing & (gap_length <= max_gap)), filled)


def clean_hourly(df, cfg):
    rules = cfg["cleaning"]
    cols = [p for p in cfg["pollutants"] if p in df.columns]
    summary = []

    def record(rule, changed):
        summary.append([rule, int(changed.any(axis=1).sum()), int(changed.sum().sum())])

    rows_before = len(df)
    df = make_hourly_grid(df)
    summary.append(["Missing hours added as empty rows", len(df) - rows_before, 0])

    changed = df[cols].isin(rules["error_codes"])
    df[cols] = df[cols].mask(changed)
    record("Error codes set to missing", changed)

    changed = pd.DataFrame(False, index=df.index, columns=cols)
    changed["CO"] = df["CO"] == 0
    df[cols] = df[cols].mask(changed)
    record("CO == 0 set to missing", changed)

    hours = rules["flatline_hours"]
    changed = pd.DataFrame({c: df.groupby("StationId")[c].transform(lambda s: flatline(s, hours))
                            for c in cols}).astype(bool)
    df[cols] = df[cols].mask(changed)
    record(f"Unchanged for {hours}+ hours set to missing", changed)

    gap = rules["max_interpolate_gap_hours"]
    before = df[cols].isna()
    for c in cols:
        df[c] = df.groupby("StationId")[c].transform(lambda s: fill_short_gaps(s, gap))
    record(f"Gaps of {gap} hours or less interpolated", before & df[cols].notna())

    return df, pd.DataFrame(summary, columns=["rule", "rows", "values"])
