import re


def find_column(columns, phrases):
    for phrase in phrases:
        for col in columns:
            if all(word in col.lower() for word in phrase.lower().split()):
                return col
    return None


def short_label(header):
    match = re.search(r"\[(.+?)\]\s*$", header)
    return match.group(1) if match else header


def count_answers(series, multi_select=False):
    answers = series.dropna().astype(str)
    if multi_select:
        answers = answers.str.split(", ").explode()
    return answers.str.strip().value_counts()


def survey_results(survey, cfg):
    scfg = cfg["survey"]
    high = scfg["rating_high_levels"]
    columns = list(survey.columns)

    harder = find_column(columns, scfg["column_keywords"]["evening_harder"])
    worst = find_column([c for c in columns if c != harder], scfg["column_keywords"]["worst_time"])
    fix = find_column([c for c in columns if c not in (harder, worst)], scfg["column_keywords"]["one_fix"])
    ratings = [c for c in columns
               if c not in (harder, worst, fix)
               and survey[c].nunique() <= 7
               and survey[c].astype(str).str.strip().isin(high).any()]
    print(f"Survey columns: harder={harder!r}, worst={worst!r}, fix={fix!r}, ratings={len(ratings)}")

    results = {}
    if harder:
        results["harder"] = (harder, count_answers(survey[harder], multi_select=True))
    if worst:
        results["worst_time"] = (worst, count_answers(survey[worst]))
    if ratings:
        counts = survey[ratings].apply(lambda s: s.astype(str).str.strip().isin(high).sum())
        counts.index = [short_label(c) for c in ratings]
        results["ratings"] = ("Rated 'A lot' or 'Severely'", counts.sort_values(ascending=False))
    if fix:
        results["one_fix"] = (fix, count_answers(survey[fix]))

    top_n = scfg["max_categories_shown"]
    return {k: (q, c.head(top_n)) for k, (q, c) in results.items()}, len(survey)
