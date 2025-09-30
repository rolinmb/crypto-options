from consts import TVURL1, TVURL2, TRADINGDAYS, TARGET_HEADERS
import re
import sys
import time
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

OPTIONS = webdriver.ChromeOptions()
OPTIONS.add_argument("--headless")
OPTIONS.add_argument("--disable-gpu")
OPTIONS.add_argument("--no-sandbox")

def parse_expiration(title):
    # Match "Sep 29, 2025 (123)"
    match = re.match(r"([A-Za-z]{3} \d{1,2}, \d{4}) \((\d+)\)", title)
    if not match:
        return None
    
    date_str, dte_str = match.groups()
    try:
        exp_date = datetime.strptime(date_str, "%b %d, %Y")
        dte = int(dte_str)
        yte = dte / TRADINGDAYS
        return [exp_date.strftime("%Y-%m-%d"), dte, round(yte, 4)]
    except ValueError:
        return None


def scrapeEntireChain(underlying, csvname):
    init_url = f"{TVURL1}{underlying}{TVURL2}"
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=OPTIONS)
    driver.get(init_url)
    print(f"src/utils.py :: Fetched TradingView option chain from {init_url}")
    time.sleep(3)
    try:
        container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.root-jBbUvk85"))
        )
        print("src/utils.py :: Successfully found root container")

        buttons = container.find_elements(By.CSS_SELECTOR, "button.item-XO65o9RZ")
        print("src/utils.py :: Successfully found expiration buttons")

        chain = {}
        for btn in buttons:
            df = None
            title = btn.get_attribute("title")
            if not title:
                print("src/utils.py :: Error parsing button title; skipping")
                continue

            parsed = parse_expiration(title)
            if not parsed:
                print("src/utils.py :: Error parsing expiration date; skipping")
                continue

            exp_date, dte, yte = parsed
            print(f"src/utils.py :: Scraping expiration {exp_date} (DTE={dte}, YTE={yte})")
            btn.click() # Click button to load table
            time.sleep(3)  # wait for table to refresh
            table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-jOonPmbB"))
            )
            headers = [th.text.strip() for th in table.find_elements(By.CSS_SELECTOR, "thead tr th")]
            headers = headers[3:]
            rows = []
            for tr in table.find_elements(By.CSS_SELECTOR, "tbody tr"):
                tds = tr.find_elements(By.TAG_NAME, "td")
                try:
                    cells = [td.text.strip() for td in tds]
                    if not cells:
                        continue
                    meaningful = [c for c in cells if c not in ("", "-")]
                    if len(meaningful) < 5:
                        continue
                    rows.append(cells)
                except Exception as e:
                    print(f"src/utils.py :: Error parsing td cells: {e}")
                    sys.exit(1)

            df = pd.DataFrame(rows, columns=TARGET_HEADERS[:-3])
            df["Expiration"] = exp_date
            df["DTE"] = dte
            df["YTE"] = yte
            df = df.replace("-", "0").replace("–", "0")
            # Convert only numeric columns (skip Expiration)
            for col in df.columns:
                if col not in ["Expiration"]:
                    df[col] = (
                        df[col]
                        .astype(str)
                        .str.replace(",", "", regex=False)
                    )
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

            chain[exp_date] = df

        final_df = pd.concat(chain.values(), ignore_index=True)[TARGET_HEADERS]
        final_df.to_csv(csvname, index=False)
        print(f"src/utils.py :: Successfully saved {underlying} futures option chain to {csvname}")
    finally:
        driver.quit()

def createSurfacePlot(underlying, csvname, mode, pngname):
    chain = pd.read_csv(csvname)
    if mode not in chain.columns:
        raise ValueError(f"Mode '{mode}' not found in CSV columns. Available: {list(chain.columns)}")

    strikes = chain["Strike"].values
    ytes = chain["YTE"].values
    zvals = chain[mode].values
    unique_strikes = np.unique(strikes)
    unique_ytes = np.unique(ytes)
    X, Y = np.meshgrid(unique_strikes, unique_ytes)
    Z = np.full_like(X, np.nan, dtype=float)
    for s, y, z in zip(strikes, ytes, zvals):
        i = np.where(unique_ytes == y)[0][0]
        j = np.where(unique_strikes == s)[0][0]
        Z[i, j] = z

    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(X, Y, Z, cmap="viridis", edgecolor="k", linewidth=0.5, antialiased=True)
    ax.set_xlabel("Strike")
    ax.set_ylabel("Years to Expiration (YTE)")
    ax.set_zlabel(mode)
    ax.set_title(f"{underlying} {mode} Surface")
    fig.colorbar(surf, shrink=0.5, aspect=10, label=mode)
    plt.tight_layout()
    plt.savefig(pngname, dpi=150)
    plt.close()
    print(f"src/utils.py :: Successfully created surface plot {pngname}")

if __name__ == "__main__":
    pass