"""Finding the survey columns and counting answers (charts 7-10)."""

import re

import pandas as pd


def find_column(columns, phrases, skip=()):
    """Return the first header that contains ALL the words of any phrase."""
    for phrase in phrases:
        words = phrase.lower().split()
        for col in columns:
            if col not in skip and all(w in col.lower() for w in words):
                return col
    return None


def short_label(header):
    """Google Forms grid headers look like 'Question [Item]' - keep just 'Item'."""
    match = re.search(r"\[(.+?)\]\s*$", header)
    return match.group(1).strip() if match else header.strip()


def find_rating_columns(survey, high_levels, skip=()):
    """Rating questions are the columns whose answers include e.g. 'A lot' / 'Severely'."""
    found = []
    for col in survey.columns:
        if col in skip:
            continue
        answers = survey[col].dropna().astype(str).str.strip()
        if answers.nunique() <= 7 and answers.isin(high_levels).any():
            found.append(col)
    return found


def count_answers(series, multi_select=False):
    """Count how often each answer was given (multi-select answers split on ', ')."""
    answers = series.dropna().astype(str)
    if multi_select:
        answers = answers.str.split(", ").explode()
    answers = answers.str.strip()
    return answers[answers != ""].value_counts()


def survey_results(survey, cfg):
    """Return a dict: chart name -> (question header, counts Series), plus total responses."""
    scfg = cfg["survey"]
    keywords = scfg["column_keywords"]
    columns = list(survey.columns)

    harder_col = find_column(columns, keywords["evening_harder"])
    worst_col = find_column(columns, keywords["worst_time"], skip=[harder_col])
    fix_col = find_column(columns, keywords["one_fix"], skip=[harder_col, worst_col])
    used = [c for c in (harder_col, worst_col, fix_col) if c]
    rating_cols = find_rating_columns(survey, scfg["rating_high_levels"], skip=used)

    print("Survey columns detected:")
    print(f"  What makes evenings harder: {harder_col}")
    print(f"  Worst time of day:          {worst_col}")
    print(f"  One thing to fix:           {fix_col}")
    print(f"  Rating questions ({len(rating_cols)}):     {[short_label(c) for c in rating_cols]}")
    if len(rating_cols) != 7:
        print(f"  NOTE: expected 7 rating questions, found {len(rating_cols)}")

    results = {}
    if harder_col:
        results["harder"] = (harder_col, count_answers(survey[harder_col], multi_select=True))
    if worst_col:
        results["worst_time"] = (worst_col, count_answers(survey[worst_col]))
    if rating_cols:
        high = scfg["rating_high_levels"]
        counts = {short_label(c): int(survey[c].astype(str).str.strip().isin(high).sum())
                  for c in rating_cols}
        results["ratings"] = ("Rated 'A lot' or 'Severely'",
                              pd.Series(counts).sort_values(ascending=False))
    if fix_col:
        results["one_fix"] = (fix_col, count_answers(survey[fix_col]))

    # Keep only the top N answers so charts stay readable
    top_n = scfg["max_categories_shown"]
    results = {k: (q, c.head(top_n)) for k, (q, c) in results.items()}
    return results, len(survey)
