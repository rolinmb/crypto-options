from consts import TVURL1, TVURL2, TRADINGDAYS
import time
from datetime import datetime
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

def calc_yte(expiration_date, trading_days):
    today = datetime.today()
    delta_days = (expiration_date - today).days
    if delta_days <= 0:
        return 0.0
    # Convert calendar days to trading days approximation
    trading_days_left = delta_days * (trading_days / TRADINGDAYS)
    return trading_days_left / trading_days  # fraction of a trading year


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

        expirations = []
        for btn in buttons:
            title = btn.get_attribute("title")
            if title:
                date_str = " ".join(title.split()[:3])  # e.g. "Sep 29, 2025"
                try:
                    parsed = datetime.strptime(date_str, "%b %d, %Y")
                    yte = calc_yte(parsed)
                    expirations.append((parsed.strftime("%Y-%m-%d"), round(yte, 4)))
                except ValueError:
                    pass

        print("src/utils.py :: Parsed expirations (with YTE):")
        for exp, yte in expirations:
            print(f" - {exp} | YTE={yte}")
    finally:
        driver.quit()

if __name__ == "__main__":
    pass