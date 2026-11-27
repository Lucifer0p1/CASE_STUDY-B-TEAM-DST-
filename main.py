"""Festival Rush in Bengaluru - reproduce the report's numbers and charts.

Run:  python main.py            (uses config.yaml)
      python main.py other.yaml (uses another config file)
"""

import os
import sys

import pandas as pd

from src import analysis, charts, cleaning, data_loading, survey

# Every key number goes into this list as (section, item, value),
# then it is printed and written to outputs/summary.md at the end.
KEY_NUMBERS = []


def note(section, item, value):
    KEY_NUMBERS.append((section, item, value))


def pct_text(count, total):
    return f"{count} ({count / total * 100:.0f}%)"


def write_summary(path):
    lines = ["# Festival Rush in Bengaluru - key numbers", ""]
    current = None
    for section, item, value in KEY_NUMBERS:
        if section != current:
            lines += ["", f"## {section}", "", "| Item | Value |", "|---|---|"]
            current = section
        lines.append(f"| {item} | {value} |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main(config_path="config.yaml"):
    cfg = data_loading.load_config(config_path)
    out = cfg["output_dir"]
    os.makedirs(out, exist_ok=True)
    acfg = cfg["analysis"]
    cpcb_source = "CPCB hourly data via Kaggle 'Air Quality Data in India 2015-2020', " \
                  f"{cfg['city']} stations, cleaned"

    # -----------------------------------------------------------------
    # Load and clean
    # -----------------------------------------------------------------
    print("\n=== Loading data ===")
    hourly, stations = data_loading.load_bengaluru_hourly(cfg)
    calendar = data_loading.load_calendar(cfg)

    print("\n=== Cleaning ===")
    clean, cleaning_summary = cleaning.clean_hourly(hourly, cfg)
    print(cleaning_summary.to_string(index=False))
    note("Data", "Stations kept", len(stations))
    note("Data", "Hourly rows loaded", f"{len(hourly):,}")
    note("Data", "Date range", f"{clean['Datetime'].min():%Y-%m-%d} to {clean['Datetime'].max():%Y-%m-%d}")
    df = analysis.add_time_columns(clean, calendar, cfg)
    note("Data", "Normal days (share of hourly rows)", f"{df['is_normal_day'].mean() * 100:.0f}%")
    for _, row in cleaning_summary.iterrows():
        note("Cleaning", row["rule"], f"{row['rows_affected']:,} rows / {row['values_affected']:,} values")

    print("\n=== Charts ===")

    # -----------------------------------------------------------------
    # Chart 1: NO2 by time of day on normal weekdays
    # -----------------------------------------------------------------
    tod = analysis.no2_by_time_of_day(df)
    peak = tod.idxmax()
    ratio = tod.max() / tod["Night (12-6 AM)"]
    charts.bar_chart(
        list(tod.index), list(tod.values), [list(tod.index).index(peak)],
        f"On normal weekdays, NO2 peaks at {peak}: {ratio:.1f}x the night level",
        cpcb_source + "; normal weekdays only", f"{out}/01_no2_time_of_day.png",
        axis_label="NO2 (µg/m³)")
    for label, value in tod.items():
        note("1. NO2 by time of day (normal weekdays, µg/m³)", label, f"{value:.1f}")
    note("1. NO2 by time of day (normal weekdays, µg/m³)", f"{peak} vs night", f"{ratio:.2f}x")

    # -----------------------------------------------------------------
    # Chart 2: NO2 at 8 PM by station
    # -----------------------------------------------------------------
    by_station = analysis.no2_8pm_by_station(df, stations, acfg["station_chart_start"])
    if len(by_station):
        top3 = list(by_station.index[:3])
        charts.bar_chart(
            list(by_station.index), list(by_station.values), [0, 1, 2],
            f"8 PM NO2 is highest at {', '.join(top3)}",
            cpcb_source + f"; 8 PM readings from {acfg['station_chart_start']} onward",
            f"{out}/02_no2_8pm_by_station.png", horizontal=True, axis_label="NO2 at 8 PM (µg/m³)")
        for name, value in by_station.items():
            note(f"2. NO2 at 8 PM by station (from {acfg['station_chart_start']}, µg/m³)", name, f"{value:.1f}")

    # -----------------------------------------------------------------
    # Chart 3: Iblur road capacity vs peak load (from config)
    # -----------------------------------------------------------------
    iblur = cfg["external"]["iblur"]
    roads = iblur["roads"]
    ratios = [r["peak_pcu"] / r["design_pcu"] for r in roads]
    worst = max(range(len(roads)), key=lambda i: ratios[i])
    charts.paired_bar_chart(
        [r["name"] for r in roads], [r["design_pcu"] for r in roads], [r["peak_pcu"] for r in roads],
        "Design capacity", "Peak load",
        f"Peak traffic is {ratios[worst]:.1f}x the design capacity on {roads[worst]['name']}",
        f"{iblur['source_name']} ({iblur['source_link']})", f"{out}/03_iblur_capacity.png",
        group_notes=[f"{r:.1f}x capacity" for r in ratios], axis_label="Vehicles (PCU per hour)")
    for r, x in zip(roads, ratios):
        note("3. Iblur road capacity (PCU)", r["name"],
             f"design {r['design_pcu']:,} vs peak {r['peak_pcu']:,} ({x:.2f}x)")

    # -----------------------------------------------------------------
    # Chart 4: TomTom travel time for 10 km (from config)
    # -----------------------------------------------------------------
    tt = cfg["external"]["tomtom"]
    tt_values = {"Average": tt["average_min"], "Morning rush": tt["morning_rush_min"],
                 "Evening rush": tt["evening_rush_min"]}
    slowest = max(tt_values, key=tt_values.get)
    extra = tt_values[slowest] - tt["average_min"]
    charts.bar_chart(
        list(tt_values), list(tt_values.values()), [list(tt_values).index(slowest)],
        f"{slowest} is the slowest: {tt_values[slowest]:.2f} min to drive 10 km, "
        f"{extra:.1f} min more than average",
        f"{tt['source_name']} ({tt['source_link']})", f"{out}/04_tomtom_travel_time.png",
        value_labels=[f"{v:.2f} min" for v in tt_values.values()], axis_label="Minutes per 10 km")
    for k, v in tt_values.items():
        note("4. TomTom 2025 - time to drive 10 km", k, f"{v} min")

    # -----------------------------------------------------------------
    # Chart 5: Festival traffic (% change in NO2)
    # -----------------------------------------------------------------
    daily = analysis.daily_no2(df, acfg["min_hours_per_day"])
    labels, changes = [], []
    for period in acfg["festival_periods"]:
        change, n = analysis.festival_change(daily, calendar, period, acfg["baseline_window_days"])
        labels.append(period["label"])
        changes.append(change)
        note("5. Festival traffic - % change in NO2 vs same-weekday median",
             period["label"], f"{change:+.1f}% (n = {n} station-days)")
    valid = [i for i, c in enumerate(changes) if pd.notna(c)]
    if valid:
        big = max(valid, key=lambda i: abs(changes[i]))
        word = "rise" if changes[big] > 0 else "drop"
        charts.bar_chart(
            labels, [0 if pd.isna(c) else c for c in changes], [big],
            f"Biggest NO2 {word}: {labels[big]}, {changes[big]:+.1f}% vs a normal same weekday",
            cpcb_source + f"; baseline = same station & weekday median, festival-free days "
                          f"within {acfg['baseline_window_days']} days",
            f"{out}/05_festival_no2_change.png",
            value_labels=["n/a" if pd.isna(c) else f"{c:+.1f}%" for c in changes],
            axis_label="Change in daily NO2 (%)")

    # -----------------------------------------------------------------
    # Chart 6: Diwali nights PM2.5, 8-10 PM vs 10 PM-midnight
    # -----------------------------------------------------------------
    nights = analysis.diwali_night_pm25(df, calendar, acfg["diwali_early_hours"], acfg["diwali_late_hours"])
    if len(nights):
        rising = int((nights["pct_increase"] > 0).sum())
        charts.paired_bar_chart(
            nights["year"].tolist(), nights["early"].tolist(), nights["late"].tolist(),
            "8-10 PM", "10 PM-midnight",
            f"On Diwali nights PM2.5 climbs after 10 PM in {rising} of {len(nights)} years",
            cpcb_source + "; Diwali eve, Diwali and Balipadyami nights, all stations",
            f"{out}/06_diwali_night_pm25.png",
            group_notes=[f"{p:+.0f}%" for p in nights["pct_increase"]], axis_label="Mean PM2.5 (µg/m³)")
        for _, r in nights.iterrows():
            note("6. Diwali nights - mean PM2.5 (µg/m³)", int(r["year"]),
                 f"8-10 PM {r['early']:.1f} -> 10 PM-12 AM {r['late']:.1f} ({r['pct_increase']:+.0f}%)")

    # -----------------------------------------------------------------
    # Charts 7-10: survey
    # -----------------------------------------------------------------
    responses = data_loading.load_survey(cfg)
    if responses is not None:
        results, total = survey.survey_results(responses, cfg)
        note("Survey", "Total responses", total)
        survey_source = f"Own Google Form survey, n = {total} ({cfg['survey']['survey_form_link']})"
        survey_charts = {
            "harder": ("07_survey_evening_harder.png", "makes evenings harder"),
            "worst_time": ("08_survey_worst_time.png", "is the worst time of day"),
            "ratings": ("09_survey_ratings.png", "affects people 'A lot' or 'Severely'"),
            "one_fix": ("10_survey_one_fix.png", "is the one thing to fix"),
        }
        for key, (filename, phrase) in survey_charts.items():
            if key not in results:
                print(f"  (no column found for survey chart '{key}' - skipped)")
                continue
            question, counts = results[key]
            top = counts.index[0]
            charts.bar_chart(
                list(counts.index), [int(v) for v in counts.values], [0],
                f"Most common answer: '{top}' {phrase} - {pct_text(int(counts.iloc[0]), total)}",
                survey_source, f"{out}/{filename}", horizontal=True,
                value_labels=[pct_text(int(v), total) for v in counts.values],
                axis_label="Respondents")
            for answer, count in counts.items():
                note(f"Survey - {question}", answer, pct_text(int(count), total))

    # -----------------------------------------------------------------
    # Text summary + summary.md
    # -----------------------------------------------------------------
    print("\n=== Key numbers ===")
    current = None
    for section, item, value in KEY_NUMBERS:
        if section != current:
            print(f"\n{section}")
            current = section
        print(f"  {item}: {value}")
    write_summary(f"{out}/summary.md")
    print(f"\nWrote {out}/summary.md")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "config.yaml")
