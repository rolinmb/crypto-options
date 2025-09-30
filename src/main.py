from consts import DIRS, MODES
from utils import scrapeEntireChain, createSurfacePlot
import sys
import os

def startupRoutine():
    if len(sys.argv) != 2:
        print("src/main.py :: Only one ticker argument required [EX. python src/main.py btc or eth]")
        sys.exit(1)

    if any(char.isdigit() for char in sys.argv[1]):
        print(f"src/main.py :: No numerical values allowed in tickers, you entered {sys.argv[1]}")
        sys.exit(1)

    if len(sys.argv[1]) != 3:
        print(f"src/main.py :: Must enter 3 characters, you entered {sys.argv[1]}")
        sys.exit(1)

    for d in DIRS:
        if not os.path.exists(d):
            os.makedirs(d)

    return sys.argv[1].upper()

if __name__ == "__main__":
    asset = startupRoutine()
    #scrapeEntireChain(asset, f"data/{asset}chain.csv")
    for mode in MODES:
        createSurfacePlot(asset, f"data/{asset}chain.csv", mode, f"img/{asset}{mode}.png")