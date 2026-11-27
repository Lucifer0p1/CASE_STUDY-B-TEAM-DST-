import re

import pandas as pd


def find_column(columns, phrases, skip=()):
    # a column matches if its header has all the words of one of the phrases
    for phrase in phrases:
        words = phrase.lower().split()
        for col in columns:
            if col in skip:
                continue
            if all(w in col.lower() for w in words):
                return col
    return None


def find_rating_columns(survey, high_levels, skip):
    rating_cols = []
    for col in survey.columns:
        if col in skip:
            continue
        answers = survey[col].dropna().astype(str).str.strip()
        if answers.nunique() <= 7 and answers.isin(high_levels).any():
            rating_cols.append(col)
    return rating_cols


def short_name(header):
    # google forms grid questions look like "How much ... ? [Traffic]"
    m = re.search(r"\[(.+?)\]\s*$", header)
    if m:
        return m.group(1)
    return header


def count_answers(col, multi=False):
    answers = col.dropna().astype(str)
    if multi:
        answers = answers.str.split(", ").explode()
    answers = answers.str.strip()
    return answers.value_counts()


def survey_results(survey, cfg):
    keywords = cfg["survey"]["column_keywords"]
    high = cfg["survey"]["rating_high_levels"]
    top_n = cfg["survey"]["max_categories_shown"]
    cols = list(survey.columns)

    harder_col = find_column(cols, keywords["evening_harder"])
    worst_col = find_column(cols, keywords["worst_time"], skip=[harder_col])
    fix_col = find_column(cols, keywords["one_fix"], skip=[harder_col, worst_col])
    rating_cols = find_rating_columns(survey, high, skip=[harder_col, worst_col, fix_col])

    print("Evenings harder column:", harder_col)
    print("Worst time column:", worst_col)
    print("One fix column:", fix_col)
    print("Rating columns found:", len(rating_cols))

    results = {}

    if harder_col:
        results["harder"] = (harder_col, count_answers(survey[harder_col], multi=True).head(top_n))

    if worst_col:
        results["worst_time"] = (worst_col, count_answers(survey[worst_col]).head(top_n))

    if rating_cols:
        counts = {}
        for c in rating_cols:
            answers = survey[c].astype(str).str.strip()
            counts[short_name(c)] = answers.isin(high).sum()
        counts = pd.Series(counts).sort_values(ascending=False)
        results["ratings"] = ("Rated 'A lot' or 'Severely'", counts.head(top_n))

    if fix_col:
        results["one_fix"] = (fix_col, count_answers(survey[fix_col]).head(top_n))

    return results, len(survey)

