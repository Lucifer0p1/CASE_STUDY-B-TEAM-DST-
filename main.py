import os

import pandas as pd

from src import analysis, charts, cleaning, data_loading, survey

cfg = data_loading.load_config()
OUT = cfg["output_dir"]
CPCB_SOURCE = "CPCB hourly data via Kaggle 'Air Quality Data in India 2015-2020', " + cfg["city"] + " stations, cleaned"

# every number that goes in the report gets added here, then printed + saved to summary.md
key_numbers = []


def add_number(section, item, value):
    key_numbers.append((section, item, value))


def n_and_pct(n, total):
    return f"{n} ({n / total * 100:.0f}%)"


def chart_time_of_day(df):
    tod = analysis.no2_by_time_of_day(df)
    peak = tod.idxmax()
    ratio = tod.max() / tod["Night (12-6 AM)"]
    highlight = [list(tod.index).index(peak)]

    charts.bar_chart(tod.index, tod.values, highlight,
                     f"On normal weekdays, NO2 peaks at {peak}: {ratio:.1f}x the night level",
                     CPCB_SOURCE + "; normal weekdays",
                     OUT + "/01_no2_time_of_day.png", axis_label="NO2 (µg/m³)")

    section = "1. NO2 by time of day, normal weekdays (µg/m³)"
    for label, val in tod.items():
        add_number(section, label, round(val, 1))
    add_number(section, f"{peak} vs night", f"{ratio:.2f}x")


def chart_stations(df, stations):
    start = cfg["analysis"]["station_chart_start"]
    by_station = analysis.no2_8pm_by_station(df, stations, start)
    top3 = list(by_station.index[:3])

    charts.bar_chart(by_station.index, by_station.values, [0, 1, 2],
                     "8 PM NO2 is highest at " + ", ".join(top3),
                     CPCB_SOURCE + "; 8 PM readings from " + start,
                     OUT + "/02_no2_8pm_by_station.png", horizontal=True, axis_label="NO2 at 8 PM (µg/m³)")

    for name, val in by_station.items():
        add_number(f"2. NO2 at 8 PM by station, from {start} (µg/m³)", name, round(val, 1))


def chart_iblur():
    iblur = cfg["external"]["iblur"]
    names = [r["name"] for r in iblur["roads"]]
    design = [r["design_pcu"] for r in iblur["roads"]]
    peak = [r["peak_pcu"] for r in iblur["roads"]]
    ratios = [p / d for p, d in zip(peak, design)]
    worst = ratios.index(max(ratios))

    charts.paired_bar_chart(names, design, peak, "Design capacity", "Peak load",
                            f"Peak traffic is {ratios[worst]:.1f}x the design capacity on {names[worst]}",
                            iblur["source_name"] + " (" + iblur["source_link"] + ")",
                            OUT + "/03_iblur_capacity.png",
                            notes=[f"{r:.1f}x capacity" for r in ratios],
                            axis_label="Vehicles (PCU per hour)")

    for i in range(len(names)):
        add_number("3. Iblur road capacity (PCU)", names[i],
                   f"design {design[i]:,} vs peak {peak[i]:,} ({ratios[i]:.2f}x)")


def chart_tomtom():
    tt = cfg["external"]["tomtom"]
    labels = ["Average", "Morning rush", "Evening rush"]
    minutes = [tt["average_min"], tt["morning_rush_min"], tt["evening_rush_min"]]
    slowest = minutes.index(max(minutes))
    extra = minutes[slowest] - minutes[0]

    charts.bar_chart(labels, minutes, [slowest],
                     f"{labels[slowest]} is the slowest: {minutes[slowest]:.2f} min to drive 10 km, "
                     f"{extra:.1f} min more than average",
                     tt["source_name"] + " (" + tt["source_link"] + ")",
                     OUT + "/04_tomtom_travel_time.png",
                     value_labels=[f"{m:.2f} min" for m in minutes], axis_label="Minutes per 10 km")

    for label, m in zip(labels, minutes):
        add_number("4. TomTom 2025, time to drive 10 km", label, f"{m} min")


def chart_festivals(df, calendar):
    a = cfg["analysis"]
    daily = analysis.daily_no2(df, a["min_hours_per_day"])

    labels = []
    changes = []
    for period in a["festival_periods"]:
        change, n = analysis.festival_change(daily, calendar, period, a["baseline_window_days"])
        if pd.isna(change):
            change = 0
        labels.append(period["label"])
        changes.append(change)
        add_number("5. Festival traffic, % change in NO2 vs same-weekday median",
                   period["label"], f"{change:+.1f}% (n = {n} station-days)")

    biggest = 0
    for i in range(len(changes)):
        if abs(changes[i]) > abs(changes[biggest]):
            biggest = i

    charts.bar_chart(labels, changes, [biggest],
                     f"Biggest NO2 change: {labels[biggest]}, {changes[biggest]:+.1f}% vs a normal same weekday",
                     CPCB_SOURCE + f"; baseline = same station and weekday median, "
                                   f"festival-free days within {a['baseline_window_days']} days",
                     OUT + "/05_festival_no2_change.png",
                     value_labels=[f"{c:+.1f}%" for c in changes], axis_label="Change in daily NO2 (%)")


def chart_diwali(df, calendar):
    a = cfg["analysis"]
    nights = analysis.diwali_night_pm25(df, calendar, a["diwali_early_hours"], a["diwali_late_hours"])
    if len(nights) == 0:
        print("No Diwali night data, skipping chart 6")
        return

    up = (nights["pct_increase"] > 0).sum()
    charts.paired_bar_chart(nights["year"], nights["early"], nights["late"], "8-10 PM", "10 PM-midnight",
                            f"On Diwali nights PM2.5 climbs after 10 PM in {up} of {len(nights)} years",
                            CPCB_SOURCE + "; Diwali eve, Diwali and Balipadyami nights",
                            OUT + "/06_diwali_night_pm25.png",
                            notes=[f"{p:+.0f}%" for p in nights["pct_increase"]],
                            axis_label="Mean PM2.5 (µg/m³)")

    for _, row in nights.iterrows():
        add_number("6. Diwali nights, mean PM2.5 (µg/m³)", int(row["year"]),
                   f"8-10 PM {row['early']:.1f} -> 10 PM-12 AM {row['late']:.1f} ({row['pct_increase']:+.0f}%)")


def survey_charts():
    responses = data_loading.load_survey(cfg)
    if responses is None:
        return

    results, total = survey.survey_results(responses, cfg)
    add_number("Survey", "Total responses", total)
    source = f"Own Google Form survey, n = {total} ({cfg['survey']['survey_form_link']})"

    to_plot = [
        ("harder", "07_survey_evening_harder.png", "makes evenings harder"),
        ("worst_time", "08_survey_worst_time.png", "is the worst time of day"),
        ("ratings", "09_survey_ratings.png", "affects people 'A lot' or 'Severely'"),
        ("one_fix", "10_survey_one_fix.png", "is the one thing to fix"),
    ]
    for key, filename, text in to_plot:
        if key not in results:
            print("Couldn't find a column for", key)
            continue

        question, counts = results[key]
        top_answer = counts.index[0]
        top_count = int(counts.iloc[0])

        charts.bar_chart(counts.index, counts.values, [0],
                         f"Most common answer: '{top_answer}' {text} - {n_and_pct(top_count, total)}",
                         source, OUT + "/" + filename, horizontal=True,
                         value_labels=[n_and_pct(int(v), total) for v in counts.values],
                         axis_label="Respondents")

        for answer, count in counts.items():
            add_number("Survey: " + question, answer, n_and_pct(int(count), total))


def print_and_save_summary():
    lines = ["# Festival Rush in Bengaluru - key numbers"]
    last_section = None

    for section, item, value in key_numbers:
        if section != last_section:
            print("\n" + section)
            lines += ["", "## " + section, "", "| Item | Value |", "|---|---|"]
            last_section = section
        print(f"  {item}: {value}")
        lines.append(f"| {item} | {value} |")

    with open(OUT + "/summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\nSaved", OUT + "/summary.md")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)

    hourly, stations = data_loading.load_bengaluru_hourly(cfg)
    calendar = data_loading.load_calendar(cfg)

    clean, cleaning_log = cleaning.clean_hourly(hourly, cfg)
    print("\nCleaning summary:")
    print(cleaning_log.to_string(index=False))

    df = analysis.add_time_columns(clean, calendar, cfg)

    add_number("Data", "Stations kept", len(stations))
    add_number("Data", "Hourly rows loaded", f"{len(hourly):,}")
    add_number("Data", "Date range", f"{df['Datetime'].min():%Y-%m-%d} to {df['Datetime'].max():%Y-%m-%d}")
    add_number("Data", "Share of hours on normal days", f"{df['is_normal_day'].mean() * 100:.0f}%")
    for _, row in cleaning_log.iterrows():
        add_number("Cleaning", row["rule"], f"{row['rows']:,} rows / {row['values']:,} values")

    print()
    chart_time_of_day(df)
    chart_stations(df, stations)
    chart_iblur()
    chart_tomtom()
    chart_festivals(df, calendar)
    chart_diwali(df, calendar)
    survey_charts()

    print_and_save_summary()
