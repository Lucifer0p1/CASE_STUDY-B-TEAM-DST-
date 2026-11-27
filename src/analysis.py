import pandas as pd


def add_time_columns(df, calendar, cfg):
    rules = cfg["normal_day"]
    not_normal = set()
    for date, festival in zip(calendar["date"], calendar["festival"]):
        if festival in rules["festivals_with_window"]:
            not_normal.update(pd.date_range(date - pd.Timedelta(days=rules["days_before"]),
                                            date + pd.Timedelta(days=rules["days_after"])))
        else:
            not_normal.add(date)

    df = df.copy()
    df["date"] = df["Datetime"].dt.normalize()
    df["hour"] = df["Datetime"].dt.hour
    df["weekday"] = df["Datetime"].dt.dayofweek
    df["is_normal_day"] = ~df["date"].isin(not_normal)
    return df


def no2_by_time_of_day(df):
    d = df[df["is_normal_day"] & (df["weekday"] < 5)]
    return pd.Series({
        "Night (12-6 AM)": d.loc[d["hour"].between(0, 5), "NO2"].mean(),
        "8 AM": d.loc[d["hour"] == 8, "NO2"].mean(),
        "Afternoon (12-4 PM)": d.loc[d["hour"].between(12, 15), "NO2"].mean(),
        "8 PM": d.loc[d["hour"] == 20, "NO2"].mean(),
    })


def no2_8pm_by_station(df, stations, start_date):
    d = df[(df["Datetime"] >= start_date) & (df["hour"] == 20)]
    result = d.groupby("StationId")["NO2"].mean().dropna()
    names = stations.set_index("StationId")["StationName"].str.split(",").str[0]
    result.index = result.index.map(names)
    return result.sort_values(ascending=False)


def daily_no2(df, min_hours):
    daily = df.groupby(["StationId", "date"]).agg(
        no2=("NO2", "mean"), hours=("NO2", "count"), is_normal_day=("is_normal_day", "first")
    ).reset_index()
    daily = daily[daily["hours"] >= min_hours]
    daily["weekday"] = daily["date"].dt.dayofweek
    return daily


def festival_change(daily, calendar, period, window_days):
    changes = []
    for fest in calendar.loc[calendar["festival"] == period["festival"], "date"]:
        window = pd.Timedelta(days=window_days)
        pool = daily[daily["is_normal_day"] & daily["date"].between(fest - window, fest + window)]
        baseline = pool.groupby(["StationId", "weekday"])["no2"].median()

        days = [fest + pd.Timedelta(days=k) for k in range(period["start_offset"], period["end_offset"] + 1)]
        festival_days = daily[daily["date"].isin(days)]
        festival_days = festival_days.join(baseline.rename("baseline"), on=["StationId", "weekday"])
        changes += list((festival_days["no2"] / festival_days["baseline"] - 1).dropna() * 100)

    if not changes:
        return float("nan"), 0
    return sum(changes) / len(changes), len(changes)


def diwali_night_pm25(df, calendar, early_hours, late_hours):
    rows = []
    bali = calendar[calendar["festival"] == "Balipadyami"]
    for diwali in calendar.loc[calendar["festival"] == "Diwali", "date"]:
        nights = [diwali - pd.Timedelta(days=1), diwali] + list(bali.loc[bali["date"].dt.year == diwali.year, "date"])
        d = df[df["date"].isin(nights)]
        early = d.loc[d["hour"].isin(early_hours), "PM2.5"].mean()
        late = d.loc[d["hour"].isin(late_hours), "PM2.5"].mean()
        if early > 0 and pd.notna(late):
            rows.append({"year": diwali.year, "early": early, "late": late,
                         "pct_increase": (late / early - 1) * 100})
    return pd.DataFrame(rows)
