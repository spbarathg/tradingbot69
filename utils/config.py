import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

class Config:
    WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")  # Keep this SECRET!
    SLIPPAGE_TOLERANCE = float(os.getenv("SLIPPAGE_TOLERANCE", "0.005"))  # 0.5% default
    PROFIT_THRESHOLD_NORMAL = float(os.getenv("PROFIT_THRESHOLD_NORMAL", "0.45")) # 45% default
    STOP_LOSS_PERCENTAGE = float(os.getenv("STOP_LOSS_PERCENTAGE", "0.10")) # 10% default
    INITIAL_INVESTMENT_USD = float(os.getenv("INITIAL_INVESTMENT_USD", "100")) # USD to start with
    DEXSCREENER_API_KEY = os.getenv("DEXSCREENER_API_KEY") #DEX Screener API
    # Jupiter API endpoint (consider different clusters if needed)
    JUPITER_API_URL = "https://quote-api.jup.ag/v6"
    # Add other configuration parameters here (API keys, etc.)

    def __init__(self):
        if not self.WALLET_PRIVATE_KEY:
            raise ValueError("Wallet private key is not set in .env file.")

config = Config()