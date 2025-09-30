from consts import TVURL1, TVURL2, TRADINGDAYS, TARGET_HEADERS
import re
import sys
import time
from datetime import datetime
import pandas as pd
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
        yte = dte / TRADINGDAYS  # fraction of trading year
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
            print(f"Scraping expiration {exp_date} (DTE={dte}, YTE={yte})")
            btn.click() # Click button to load table
            time.sleep(3)  # wait for table to refresh
            # TODO: Click button and scrape html table class '.table-jOonPmbB'
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
            df.replace("-", 0.0)
            for col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="ignore")
                
            chain[exp_date] = df

        final_df = pd.concat(chain.values(), ignore_index=True)[TARGET_HEADERS]
        final_df.to_csv(csvname, index=False)
        print(f"src/utils.py :: Successfully saved {underlying} futures option chain to {csvname}")
    finally:
        driver.quit()

if __name__ == "__main__":
    pass