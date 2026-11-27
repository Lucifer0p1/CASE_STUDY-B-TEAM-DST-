import os

import pandas as pd

from src import analysis, charts, cleaning, data_loading, survey

numbers = []


def note(section, item, value):
    numbers.append((section, item, value))


def share(count, total):
    return f"{count} ({count / total * 100:.0f}%)"


def write_summary(path):
    lines = ["# Festival Rush in Bengaluru - key numbers"]
    last = None
    for section, item, value in numbers:
        if section != last:
            lines += ["", f"## {section}", "", "| Item | Value |", "|---|---|"]
            last = section
        lines.append(f"| {item} | {value} |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    cfg = data_loading.load_config()
    out = cfg["output_dir"]
    a = cfg["analysis"]
    os.makedirs(out, exist_ok=True)
    cpcb = f"CPCB hourly data via Kaggle 'Air Quality Data in India 2015-2020', {cfg['city']} stations, cleaned"

    hourly, stations = data_loading.load_bengaluru_hourly(cfg)
    calendar = data_loading.load_calendar(cfg)

    clean, cleaning_summary = cleaning.clean_hourly(hourly, cfg)
    print("\nCleaning summary")
    print(cleaning_summary.to_string(index=False))

    df = analysis.add_time_columns(clean, calendar, cfg)
    note("Data", "Stations kept", len(stations))
    note("Data", "Hourly rows loaded", f"{len(hourly):,}")
    note("Data", "Date range", f"{df['Datetime'].min():%Y-%m-%d} to {df['Datetime'].max():%Y-%m-%d}")
    note("Data", "Share of hours on normal days", f"{df['is_normal_day'].mean() * 100:.0f}%")
    for rule, rows, values in cleaning_summary.values:
        note("Cleaning", rule, f"{rows:,} rows / {values:,} values")

    print()

    tod = analysis.no2_by_time_of_day(df)
    peak = tod.idxmax()
    ratio = tod.max() / tod["Night (12-6 AM)"]
    charts.bar_chart(tod.index, tod.values, [list(tod.index).index(peak)],
                     f"On normal weekdays, NO2 peaks at {peak}: {ratio:.1f}x the night level",
                     cpcb + "; normal weekdays", f"{out}/01_no2_time_of_day.png", axis_label="NO2 (µg/m³)")
    for label, value in tod.items():
        note("1. NO2 by time of day, normal weekdays (µg/m³)", label, f"{value:.1f}")
    note("1. NO2 by time of day, normal weekdays (µg/m³)", f"{peak} vs night", f"{ratio:.2f}x")

    stn = analysis.no2_8pm_by_station(df, stations, a["station_chart_start"])
    charts.bar_chart(stn.index, stn.values, [0, 1, 2],
                     f"8 PM NO2 is highest at {', '.join(stn.index[:3])}",
                     cpcb + f"; 8 PM readings from {a['station_chart_start']}",
                     f"{out}/02_no2_8pm_by_station.png", horizontal=True, axis_label="NO2 at 8 PM (µg/m³)")
    for name, value in stn.items():
        note(f"2. NO2 at 8 PM by station, from {a['station_chart_start']} (µg/m³)", name, f"{value:.1f}")

    iblur = cfg["external"]["iblur"]
    roads = iblur["roads"]
    ratios = [r["peak_pcu"] / r["design_pcu"] for r in roads]
    worst = ratios.index(max(ratios))
    charts.paired_bar_chart([r["name"] for r in roads], [r["design_pcu"] for r in roads],
                            [r["peak_pcu"] for r in roads], "Design capacity", "Peak load",
                            f"Peak traffic is {ratios[worst]:.1f}x the design capacity on {roads[worst]['name']}",
                            f"{iblur['source_name']} ({iblur['source_link']})", f"{out}/03_iblur_capacity.png",
                            notes=[f"{r:.1f}x capacity" for r in ratios], axis_label="Vehicles (PCU per hour)")
    for r, x in zip(roads, ratios):
        note("3. Iblur road capacity (PCU)", r["name"], f"design {r['design_pcu']:,} vs peak {r['peak_pcu']:,} ({x:.2f}x)")

    tt = cfg["external"]["tomtom"]
    times = {"Average": tt["average_min"], "Morning rush": tt["morning_rush_min"], "Evening rush": tt["evening_rush_min"]}
    slowest = max(times, key=times.get)
    charts.bar_chart(times.keys(), times.values(), [list(times).index(slowest)],
                     f"{slowest} is the slowest: {times[slowest]:.2f} min to drive 10 km, "
                     f"{times[slowest] - times['Average']:.1f} min more than average",
                     f"{tt['source_name']} ({tt['source_link']})", f"{out}/04_tomtom_travel_time.png",
                     value_labels=[f"{v:.2f} min" for v in times.values()], axis_label="Minutes per 10 km")
    for k, v in times.items():
        note("4. TomTom 2025, time to drive 10 km", k, f"{v} min")

    daily = analysis.daily_no2(df, a["min_hours_per_day"])
    labels, changes = [], []
    for period in a["festival_periods"]:
        change, n = analysis.festival_change(daily, calendar, period, a["baseline_window_days"])
        labels.append(period["label"])
        changes.append(0 if pd.isna(change) else change)
        note("5. Festival traffic, % change in NO2 vs same-weekday median", period["label"], f"{change:+.1f}% (n = {n} station-days)")
    big = max(range(len(changes)), key=lambda i: abs(changes[i]))
    charts.bar_chart(labels, changes, [big],
                     f"Biggest NO2 change: {labels[big]}, {changes[big]:+.1f}% vs a normal same weekday",
                     cpcb + f"; baseline = same station and weekday median, festival-free days within {a['baseline_window_days']} days",
                     f"{out}/05_festival_no2_change.png",
                     value_labels=[f"{c:+.1f}%" for c in changes], axis_label="Change in daily NO2 (%)")

    nights = analysis.diwali_night_pm25(df, calendar, a["diwali_early_hours"], a["diwali_late_hours"])
    if len(nights):
        rising = (nights["pct_increase"] > 0).sum()
        charts.paired_bar_chart(nights["year"], nights["early"], nights["late"], "8-10 PM", "10 PM-midnight",
                                f"On Diwali nights PM2.5 climbs after 10 PM in {rising} of {len(nights)} years",
                                cpcb + "; Diwali eve, Diwali and Balipadyami nights", f"{out}/06_diwali_night_pm25.png",
                                notes=[f"{p:+.0f}%" for p in nights["pct_increase"]], axis_label="Mean PM2.5 (µg/m³)")
        for r in nights.itertuples():
            note("6. Diwali nights, mean PM2.5 (µg/m³)", r.year,
                 f"8-10 PM {r.early:.1f} -> 10 PM-12 AM {r.late:.1f} ({r.pct_increase:+.0f}%)")

    responses = data_loading.load_survey(cfg)
    if responses is not None:
        results, total = survey.survey_results(responses, cfg)
        note("Survey", "Total responses", total)
        source = f"Own Google Form survey, n = {total} ({cfg['survey']['survey_form_link']})"
        survey_charts = [
            ("harder", "07_survey_evening_harder.png", "makes evenings harder"),
            ("worst_time", "08_survey_worst_time.png", "is the worst time of day"),
            ("ratings", "09_survey_ratings.png", "affects people 'A lot' or 'Severely'"),
            ("one_fix", "10_survey_one_fix.png", "is the one thing to fix"),
        ]
        for key, filename, phrase in survey_charts:
            if key not in results:
                continue
            question, counts = results[key]
            charts.bar_chart(counts.index, counts.values, [0],
                             f"Most common answer: '{counts.index[0]}' {phrase} - {share(counts.iloc[0], total)}",
                             source, f"{out}/{filename}", horizontal=True,
                             value_labels=[share(v, total) for v in counts.values], axis_label="Respondents")
            for answer, count in counts.items():
                note(f"Survey: {question}", answer, share(count, total))

    last = None
    for section, item, value in numbers:
        if section != last:
            print(f"\n{section}")
            last = section
        print(f"  {item}: {value}")
    write_summary(f"{out}/summary.md")
    print(f"\nWrote {out}/summary.md")


if __name__ == "__main__":
    main()
