import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()  # Load environment variables from .env file
        self.WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
        self.SLIPPAGE_TOLERANCE = float(os.getenv("SLIPPAGE_TOLERANCE", 0.005))  # 0.5% default
        self.PROFIT_THRESHOLD_NORMAL = float(os.getenv("PROFIT_THRESHOLD_NORMAL", 0.45))  # 45% default
        self.STOP_LOSS_PERCENTAGE = float(os.getenv("STOP_LOSS_PERCENTAGE", 0.10))  # 10% default
        self.INITIAL_INVESTMENT_USD = float(os.getenv("INITIAL_INVESTMENT_USD", 100))  # USD default
        self.DEXSCREENER_API_KEY = os.getenv("DEXSCREENER_API_KEY")  # DEX Screener API
        self.JUPITER_API_URL = os.getenv("JUPITER_API_URL", "https://quote-api.jup.ag/v6")  # Jupiter API default

        if not self.WALLET_PRIVATE_KEY:
            raise ValueError("Wallet private key is not set in the .env file.")

# Usage
config = Config()