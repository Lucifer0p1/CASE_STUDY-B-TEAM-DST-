import pandas as pd


def get_non_normal_dates(calendar, cfg):
    before = cfg["normal_day"]["days_before"]
    after = cfg["normal_day"]["days_after"]
    big_festivals = cfg["normal_day"]["festivals_with_window"]

    dates = set()
    for _, row in calendar.iterrows():
        if row["festival"] in big_festivals:
            start = row["date"] - pd.Timedelta(days=before)
            end = row["date"] + pd.Timedelta(days=after)
            for d in pd.date_range(start, end):
                dates.add(d)
        else:
            # holidays and lockdown days - just that one day
            dates.add(row["date"])
    return dates


def add_time_columns(df, calendar, cfg):
    df = df.copy()
    df["date"] = df["Datetime"].dt.normalize()
    df["hour"] = df["Datetime"].dt.hour
    df["weekday"] = df["Datetime"].dt.dayofweek  # monday = 0

    bad_dates = get_non_normal_dates(calendar, cfg)
    df["is_normal_day"] = ~df["date"].isin(bad_dates)
    return df


def no2_by_time_of_day(df):
    wd = df[(df["is_normal_day"]) & (df["weekday"] < 5)]

    night = wd[wd["hour"] <= 5]["NO2"].mean()
    morning = wd[wd["hour"] == 8]["NO2"].mean()
    afternoon = wd[(wd["hour"] >= 12) & (wd["hour"] <= 15)]["NO2"].mean()
    evening = wd[wd["hour"] == 20]["NO2"].mean()

    return pd.Series({
        "Night (12-6 AM)": night,
        "8 AM": morning,
        "Afternoon (12-4 PM)": afternoon,
        "8 PM": evening,
    })


def no2_8pm_by_station(df, stations, start_date):
    sub = df[(df["Datetime"] >= start_date) & (df["hour"] == 20)]
    avg = sub.groupby("StationId")["NO2"].mean().dropna()

    # station names are long like "BTM Layout, Bengaluru - CPCB", just keep the first bit
    names = {}
    for _, row in stations.iterrows():
        names[row["StationId"]] = row["StationName"].split(",")[0]
    avg.index = [names.get(i, i) for i in avg.index]

    return avg.sort_values(ascending=False)


def daily_no2(df, min_hours):
    daily = df.groupby(["StationId", "date"]).agg(
        no2=("NO2", "mean"),
        hours=("NO2", "count"),
        is_normal_day=("is_normal_day", "first"),
    ).reset_index()

    # don't trust days with lots of missing hours
    daily = daily[daily["hours"] >= min_hours].copy()
    daily["weekday"] = daily["date"].dt.dayofweek
    return daily


def festival_change(daily, calendar, period, window_days):
    fest_dates = calendar[calendar["festival"] == period["festival"]]["date"]
    all_changes = []

    for fest in fest_dates:
        # baseline = normal days within +/- window_days, median per station and weekday
        lo = fest - pd.Timedelta(days=window_days)
        hi = fest + pd.Timedelta(days=window_days)
        normal = daily[(daily["is_normal_day"]) & (daily["date"] >= lo) & (daily["date"] <= hi)]
        baseline = normal.groupby(["StationId", "weekday"])["no2"].median().rename("baseline")

        days = []
        for k in range(period["start_offset"], period["end_offset"] + 1):
            days.append(fest + pd.Timedelta(days=k))

        fest_days = daily[daily["date"].isin(days)]
        fest_days = fest_days.join(baseline, on=["StationId", "weekday"])
        pct = (fest_days["no2"] / fest_days["baseline"] - 1) * 100
        all_changes.extend(pct.dropna().tolist())

    if len(all_changes) == 0:
        return float("nan"), 0
    return sum(all_changes) / len(all_changes), len(all_changes)


def diwali_night_pm25(df, calendar, early_hours, late_hours):
    diwali_dates = calendar[calendar["festival"] == "Diwali"]["date"]
    bali = calendar[calendar["festival"] == "Balipadyami"]

    results = []
    for diwali in diwali_dates:
        eve = diwali - pd.Timedelta(days=1)
        bali_day = bali[bali["date"].dt.year == diwali.year]["date"].tolist()
        nights = [eve, diwali] + bali_day

        sub = df[df["date"].isin(nights)]
        early = sub[sub["hour"].isin(early_hours)]["PM2.5"].mean()
        late = sub[sub["hour"].isin(late_hours)]["PM2.5"].mean()

        if pd.isna(early) or pd.isna(late) or early == 0:
            continue  # no data that year

        results.append({
            "year": diwali.year,
            "early": early,
            "late": late,
            "pct_increase": (late - early) / early * 100,
        })

    return pd.DataFrame(results)
