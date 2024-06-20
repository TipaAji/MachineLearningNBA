import os
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import time
import asyncio

SEASONS = list(range(2017, 2024))

DATA_DIR = "data"
STANDINGS_DIR = os.path.join(DATA_DIR, "standings")
SCORES_DIR = os.path.join(DATA_DIR, "scores")

async def getHtml(url, selector, sleep=5, retries=3):
    html = None
    for i in range(1, retries + 1):
        time.sleep(sleep * i)

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                await page.goto(url)
                print(await page.title())
                html = await page.inner_html(selector)

        except PlaywrightTimeout:
            print(f"Timeout error: {url}")
            continue

        else:
            break

    return html


async def scrapeSeason(season):
    url = f"https://www.basketball-reference.com/leagues/NBA_{season}_games.html"
    html = await getHtml(url, "#content .filter")

    soup = BeautifulSoup(html)
    links = soup.find_all("a")
    href = [l["href"] for l in links]
    standingsPages = [f"https://basketball-reference.com{l}" for l in href]

    for url in standingsPages:
        savePath = os.path.join(STANDINGS_DIR, url.split("/")[-1])
        if os.path.exists(savePath):
            continue

        html = await getHtml(url, "#all_schedule")
        with open(savePath, "w+") as f:
            f.write(html)


# for season in SEASONS:
#     asyncio.run(scrapeSeason(season))

standingsFiles = os.listdir(STANDINGS_DIR)

async def scrapeGame(standingsFile):
    with open(standingsFile, 'r') as f:
        html = f.read()

    soup = BeautifulSoup(html)
    links = soup.find_all("a")
    hrefs = [l.get("href") for l in links]
    boxScores = [l for l in hrefs if l and "boxscore" in l and ".html" in l]
    boxScores = [f"https://www.basketball-reference.com{l}" for l in boxScores]

    for url in boxScores:
        savePath = os.path.join(SCORES_DIR, url.split("/")[-1])
        if os.path.exists(savePath):
            continue

        html = await getHtml(url, "#content")

        if not html:
            continue

        with open(savePath, "w+", encoding="utf-8") as f:
            f.write(html)

standingsFiles = [s for s in standingsFiles if ".html" in s]
for f in standingsFiles:
    filepath = os.path.join(STANDINGS_DIR, f)
    asyncio.run(scrapeGame(filepath))