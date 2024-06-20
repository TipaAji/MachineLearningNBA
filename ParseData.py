import os
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO

SCORES_DIR = "data/scores"

boxScores = os.listdir(SCORES_DIR)

boxScores = [os.path.join(SCORES_DIR, f) for f in boxScores if f.endswith(".html")]

def parseHtml(boxScore):
    with open(boxScore, encoding="utf-8", errors="ignore") as f:
        html = f.read()

    soups = BeautifulSoup(html, "html.parser")
    [s.decompose() for s in soups.select("tr.over_header")]
    [s.decompose() for s in soups.select("tr.thead")]

    return soups

def readLineScore(soup):
    line_score = pd.read_html(StringIO(str(soup)), attrs={'id': 'line_score'},flavor='html5lib')[0]
    cols = list(line_score.columns)
    cols[0] = "team"
    cols[-1] = "total"
    line_score.columns = cols

    line_score = line_score[["team", "total"]]

    return line_score

def readStats(soup, team, stat):
    df = pd.read_html(StringIO(str(soup)), attrs={'id': f'box-{team}-game-{stat}'}, index_col = 0, flavor='html5lib')[0]
    df = df.apply(pd.to_numeric, errors="coerce")
    return df

def readSeasonInfo(soup):
    nav = soup.select("#bottom_nav_container")[0]
    hrefs = [a["href"] for a in nav.find_all("a")]
    season = os.path.basename(hrefs[1]).split("_")[0]
    return season

baseCols = None
games = []

for boxScore in boxScores:
    soup = parseHtml(boxScore)
    lineScore = readLineScore(soup)
    teams = list(lineScore["team"])

    summaries = []
    for team in teams:
        basic = readStats(soup, team, "basic")
        advanced = readStats(soup, team, "advanced")

        totals = pd.concat([basic.iloc[-1,:], advanced.iloc[-1,:]])
        totals.index = totals.index.str.lower()

        maxes = pd.concat([basic.iloc[:-1].max(), advanced.iloc[:-1].max()])
        maxes.index = maxes.index.str.lower() + "_max"

        summary = pd.concat([totals, maxes])

        if baseCols is None:
            baseCols = list(summary.index.drop_duplicates(keep="first"))
            baseCols = [b for b in baseCols if "bpm" not in b]

        summary = summary[baseCols]
        summaries.append(summary)

    summary = pd.concat(summaries, axis=1).T

    game = pd.concat([summary, lineScore], axis=1)

    game["home"] = [0, 1]
    gameOpp = game.iloc[::-1].reset_index()
    gameOpp.columns += "_opp"

    fullGame = pd.concat([game, gameOpp], axis=1)

    fullGame["season"] = readSeasonInfo(soup)

    fullGame["date"] = os.path.basename(boxScore)[:8]
    fullGame["date"] = pd.to_datetime(fullGame["date"], format="%Y%m%d")

    fullGame["won"] = fullGame["total"] > fullGame["total_opp"]
    games.append(fullGame)

    if len(games) % 100 == 0:
        print(f"{len(games)} / {len(boxScores)}")

games = [g for g in games if isinstance(g, pd.DataFrame) and g.shape[1] == 150]
gamesDf = pd.concat(games, ignore_index=True)
gamesDf.to_csv("nba_games.csv")
