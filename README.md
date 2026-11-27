# Festival Rush in Bengaluru

This project reproduces the numbers and charts from the report "Festival Rush in Bengaluru".
It cleans CPCB hourly air-quality data for Bengaluru's 10 stations and uses NO2 (a traffic proxy) and PM2.5 to compare normal days, rush hours and festival periods.
It also adds traffic figures from news sources and charts the results of a small Google Form survey.

## Data links

- CPCB dataset (Kaggle): https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india (download `station_hour.csv` and `stations.csv`)
- Original source (CPCB CCR): https://airquality.cpcb.gov.in/ccr/
- My Google Form survey: https://docs.google.com/forms/d/e/1FAIpQLScbg78EQ6XAj2tEmOb1jmZnpGqzfPW5GkGIaIV8pCZJBKTYvw/viewform
- Survey responses sheet: https://docs.google.com/spreadsheets/d/1JQhw3YinAIUP3Z6FntmVpdnCmEH0M57-kJiWfMexPaI/edit?usp=sharing
- Survey responses as CSV (read by the code): https://docs.google.com/spreadsheets/d/1JQhw3YinAIUP3Z6FntmVpdnCmEH0M57-kJiWfMexPaI/export?format=csv

### External sources (figures used in charts and recommendations)

| Figure | Source |
|---|---|
| TomTom Traffic Index, time to drive 10 km | https://www.tomtom.com/traffic-index/bengaluru-traffic |
| Bengaluru Traffic Police Iblur capacity study | https://www.deccanherald.com/india/karnataka/bengaluru/study-by-bengaluru-traffic-police-reveals-vehicle-movement-exceeds-road-capacity-on-orr-sarjapur-road-3774552 |
| AI signals cut travel time by 33% | https://www.deccanherald.com/india/karnataka/bengaluru/ai-powered-signals-in-bengaluru-reduce-travel-time-by-33-3226394 |
| Traffic down 20% at 75 AI-signal junctions | https://magzter.com/stories/newspaper/The-New-Indian-Express-Bengaluru/TRAFFIC-DOWN-BY-20-AT-75-KEY-JUNCTIONS-ARE-AI-SIGNALS-HELPING |
| Metro record ridership | https://www.deccanherald.com/india/karnataka/bengaluru/rcb-celebrations-push-metro-ridership-to-highest-ever-3575348 |
| Metro average ridership | https://www.deccanherald.com/amp/story/india%2Fkarnataka%2Fbengaluru%2Fnamma-metros-average-ridership-falls-marginally-in-may-3597961 |
| Metro 5-minute evening frequency | https://www.deccanherald.com/india/karnataka/bengaluru/bengaluru-metro-5-min-frequency-for-itpl-mysuru-road-from-356-pm-to-8-pm-3447381 |
| Metro extended on New Year's Eve | https://theprint.in/india/bmrcl-extends-metro-services-on-new-years-eve/2814444/ |

## Setup

1. Install Python 3.9+ and then the packages:

   ```bash
   pip install -r requirements.txt
   ```

2. Download the Kaggle dataset and put these two files in `data/`:

   ```
   data/station_hour.csv
   data/stations.csv
   data/festival_calendar.csv   (already included)
   ```

3. Survey responses are read straight from the Google Sheet (CSV link in `config.yaml`).
   The sheet must be shared as "Anyone with the link can view". To use a local file instead,
   export the responses to `data/survey_responses.csv` and set `survey_responses_csv` to that path.
   If the survey can't be read, the survey charts are skipped and everything else still runs.

4. `config.yaml` already has all the links filled in. You only need to edit it to change file
   paths, the cleaning rules, the "normal day" window, or the survey column keywords
   (columns are found by matching words in the question headers).

5. Run:

   ```bash
   python main.py
   ```

   The cleaning summary and every key number are printed in the terminal.
   Charts are saved to `outputs/` and all numbers to `outputs/summary.md`.

## Project layout

| File | What it does |
|---|---|
| `main.py` | Runs everything in order: load, clean, analyse, chart, summarise |
| `src/data_loading.py` | Reads config, CPCB files (Bengaluru only), festival calendar, survey |
| `src/cleaning.py` | Cleaning rules (error codes, CO = 0, flat-lines, short-gap interpolation) |
| `src/analysis.py` | Normal-day flag and the numbers for charts 1, 2, 5, 6 |
| `src/survey.py` | Finds survey columns and counts answers (charts 7-10) |
| `src/charts.py` | Bar-chart helpers (blue highlight, grey bars, source line) |

## Cleaning rules

1. Each station gets one row per hour (missing hours become empty rows).
2. Codes 999.99 and 499.99 are set to missing.
3. CO == 0 is set to missing.
4. Values unchanged for 6+ hours at a station are set to missing.
5. Gaps of 3 hours or less are filled with linear interpolation; longer gaps stay empty.

A **normal day** is not within 21 days before or 14 days after Diwali, Dasara or Ganesh Chaturthi,
not a holiday (Jan 26, May 1, Aug 15, Oct 2, Nov 1, Dec 25, Balipadyami), and not in the
COVID lockdown (2020-03-25 to 2020-05-31).

## Outputs

| Output | Question it answers |
|---|---|
| `01_no2_time_of_day.png` | On normal weekdays, when in the day is NO2 (traffic) highest: night, 8 AM, afternoon or 8 PM? |
| `02_no2_8pm_by_station.png` | Which stations have the worst 8 PM NO2 (July 2018 onward)? |
| `03_iblur_capacity.png` | How far does peak traffic exceed road design capacity at Iblur? |
| `04_tomtom_travel_time.png` | How much longer does 10 km take in the morning and evening rush? |
| `05_festival_no2_change.png` | Does NO2 change before Dasara, after Ganesh Chaturthi and before Diwali vs a normal same weekday? |
| `06_diwali_night_pm25.png` | On Diwali nights, how much does PM2.5 rise from 8-10 PM to 10 PM-midnight each year? |
| `07_survey_evening_harder.png` | What makes evenings harder for respondents? |
| `08_survey_worst_time.png` | Which time of day do respondents find worst? |
| `09_survey_ratings.png` | Which issues affect people "A lot" or "Severely"? |
| `10_survey_one_fix.png` | What one thing would respondents fix first? |
| `summary.md` | Every key number used in the report |

## Limitations

- **NO2 is only a traffic proxy.** It also comes from other burning sources and depends on weather, so it shows traffic patterns, not vehicle counts.
- **Thin data before 2018.** Only a few Bengaluru stations reported before 2018, so earlier years (and early festival comparisons) rest on fewer stations.
- **The survey is small.** It is a convenience sample from one Google Form, so the percentages describe respondents, not all of Bengaluru.
- The TomTom and traffic police figures are copied from news sources and are not recomputed here.

## Use of AI

We used an AI coding assistant (Claude) to help write and tidy up the Python code in this project.
The analysis questions, the festival calendar, the survey and the interpretation of the results are our own,
and we checked the code and its outputs ourselves.
