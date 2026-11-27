# Festival Rush in Bengaluru

This project reproduces the numbers and charts from the report "Festival Rush in Bengaluru".
It cleans CPCB hourly air-quality data for Bengaluru's 10 stations and uses NO2 (a traffic proxy) and PM2.5 to compare normal days, rush hours and festival periods.
It also adds traffic figures from news sources and charts the results of a small Google Form survey.

## Data links

- CPCB dataset (Kaggle): <PASTE LINK>
- Original source (CPCB CCR): <PASTE LINK>
- My Google Form survey: <PASTE FORM LINK>
- Survey responses sheet: <PASTE SHEET LINK>

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

3. Survey responses: either export the Google Form responses to `data/survey_responses.csv`,
   or put a Google Sheets CSV link in `config.yaml`:
   `https://docs.google.com/spreadsheets/d/<ID>/export?format=csv`
   (the sheet must be shared as "Anyone with the link can view").
   If no survey file is found, the survey charts are skipped and everything else still runs.

4. Edit `config.yaml`:
   - paste the dataset, form and news-source links in place of the `<PASTE ...>` placeholders
   - change file paths if your files live somewhere else
   - optional: tweak the cleaning rules, the "normal day" window, or the survey column keywords
     (columns are found by matching words in the question headers)

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
