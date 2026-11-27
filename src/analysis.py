"""The numbers behind the air-quality charts (charts 1, 2, 5 and 6)."""

import pandas as pd


# ---------------------------------------------------------------------
# Normal days
# ---------------------------------------------------------------------
def excluded_dates(calendar, cfg):
    """All dates that are NOT normal days (festival windows, holidays, lockdown)."""
    rules = cfg["normal_day"]
    excluded = set()
    for _, row in calendar.iterrows():
        if row["festival"] in rules["festivals_with_window"]:
            start = row["date"] - pd.Timedelta(days=rules["days_before"])
            end = row["date"] + pd.Timedelta(days=rules["days_after"])
            excluded.update(pd.date_range(start, end))
        else:
            excluded.add(row["date"])   # fixed holiday, Balipadyami or a lockdown day
    return excluded


def add_time_columns(df, calendar, cfg):
    """Add date, hour, weekday (0 = Monday) and is_normal_day columns."""
    df = df.copy()
    df["date"] = df["Datetime"].dt.normalize()
    df["hour"] = df["Datetime"].dt.hour
    df["weekday"] = df["Datetime"].dt.dayofweek
    df["is_normal_day"] = ~df["date"].isin(excluded_dates(calendar, cfg))
    return df


# ---------------------------------------------------------------------
# Chart 1: NO2 by time of day on normal weekdays
# ---------------------------------------------------------------------
def no2_by_time_of_day(df):
    weekdays = df[df["is_normal_day"] & (df["weekday"] < 5)]
    no2 = weekdays["NO2"]
    return pd.Series({
        "Night (12-6 AM)": no2[weekdays["hour"].between(0, 5)].mean(),
        "8 AM": no2[weekdays["hour"] == 8].mean(),
        "Afternoon (12-4 PM)": no2[weekdays["hour"].between(12, 15)].mean(),
        "8 PM": no2[weekdays["hour"] == 20].mean(),
    })


# ---------------------------------------------------------------------
# Chart 2: NO2 at 8 PM by station
# ---------------------------------------------------------------------
def no2_8pm_by_station(df, stations, start_date):
    recent = df[(df["Datetime"] >= pd.Timestamp(start_date)) & (df["hour"] == 20)]
    by_station = recent.groupby("StationId")["NO2"].mean().dropna()
    names = stations.set_index("StationId")["StationName"]
    # Use the short station name (text before the first comma)
    by_station.index = [str(names.get(sid, sid)).split(",")[0] for sid in by_station.index]
    return by_station.sort_values(ascending=False)


# ---------------------------------------------------------------------
# Chart 5: festival traffic (% change in NO2 vs a same-weekday baseline)
# ---------------------------------------------------------------------
def daily_no2(df, min_hours):
    """Daily mean NO2 per station, keeping only days with enough hourly values."""
    daily = (df.groupby(["StationId", "date"])
               .agg(no2=("NO2", "mean"), hours=("NO2", "count"),
                    is_normal_day=("is_normal_day", "first"))
               .reset_index())
    daily = daily[daily["hours"] >= min_hours].copy()
    daily["weekday"] = daily["date"].dt.dayofweek
    return daily


def festival_change(daily, calendar, period, window_days):
    """Average % change in daily NO2 during one festival period.

    For each station and each day in the period, compare that day's NO2 with the
    median of the same station on the same weekday, using only normal
    (festival-free) days within `window_days` either side of the festival.
    """
    changes = []
    festival_dates = calendar.loc[calendar["festival"] == period["festival"], "date"]
    for fest_date in festival_dates:
        lo = fest_date - pd.Timedelta(days=window_days)
        hi = fest_date + pd.Timedelta(days=window_days)
        baseline_pool = daily[daily["is_normal_day"] & daily["date"].between(lo, hi)]
        baseline = baseline_pool.groupby(["StationId", "weekday"])["no2"].median()

        period_days = [fest_date + pd.Timedelta(days=k)
                       for k in range(period["start_offset"], period["end_offset"] + 1)]
        in_period = daily[daily["date"].isin(period_days)]
        for _, row in in_period.iterrows():
            base = baseline.get((row["StationId"], row["weekday"]))
            if base is not None and base > 0:
                changes.append((row["no2"] / base - 1) * 100)
    mean_change = sum(changes) / len(changes) if changes else float("nan")
    return mean_change, len(changes)


# ---------------------------------------------------------------------
# Chart 6: Diwali nights, PM2.5 at 8-10 PM vs 10 PM-midnight
# ---------------------------------------------------------------------
def diwali_night_pm25(df, calendar, early_hours, late_hours):
    rows = []
    diwali = calendar[calendar["festival"] == "Diwali"]
    bali = calendar[calendar["festival"] == "Balipadyami"]
    for fest_date in diwali["date"]:
        year = fest_date.year
        bali_dates = bali.loc[bali["date"].dt.year == year, "date"].tolist()
        nights = [fest_date - pd.Timedelta(days=1), fest_date] + bali_dates
        sub = df[df["date"].isin(nights)]
        early = sub.loc[sub["hour"].isin(early_hours), "PM2.5"].mean()
        late = sub.loc[sub["hour"].isin(late_hours), "PM2.5"].mean()
        if pd.notna(early) and pd.notna(late) and early > 0:
            rows.append({"year": year, "early": early, "late": late,
                         "pct_increase": (late / early - 1) * 100})
    return pd.DataFrame(rows)
