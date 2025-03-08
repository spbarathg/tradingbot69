import os
from dotenv import load_dotenv
from typing import Optional, Union
from functools import lru_cache


class Config:
    def __init__(self):
        """Initialize configuration by loading environment variables from .env file."""
        load_dotenv()  # Load environment variables from .env file
        self._validate_required_keys()

    def _validate_required_keys(self) -> None:
        """Validate that all required environment variables are set."""
        required_keys = ["WALLET_PRIVATE_KEY"]
        for key in required_keys:
            if not os.getenv(key):
                raise ValueError(f"Required environment variable '{key}' is not set in the .env file.")

    @lru_cache(maxsize=1)
    def get_wallet_private_key(self) -> str:
        """Get the wallet private key from environment variables."""
        return os.getenv("WALLET_PRIVATE_KEY")

    @lru_cache(maxsize=1)
    def get_slippage_tolerance(self) -> float:
        """Get the slippage tolerance from environment variables with a default fallback."""
        return float(os.getenv("SLIPPAGE_TOLERANCE", 0.005))  # 0.5% default

    @lru_cache(maxsize=1)
    def get_profit_threshold_normal(self) -> float:
        """Get the profit threshold from environment variables with a default fallback."""
        return float(os.getenv("PROFIT_THRESHOLD_NORMAL", 0.45))  # 45% default

    @lru_cache(maxsize=1)
    def get_stop_loss_percentage(self) -> float:
        """Get the stop-loss percentage from environment variables with a default fallback."""
        return float(os.getenv("STOP_LOSS_PERCENTAGE", 0.10))  # 10% default

    @lru_cache(maxsize=1)
    def get_initial_investment_usd(self) -> float:
        """Get the initial investment amount in USD from environment variables with a default fallback."""
        return float(os.getenv("INITIAL_INVESTMENT_USD", 100))  # USD default

    @lru_cache(maxsize=1)
    def get_dexscreener_api_key(self) -> Optional[str]:
        """Get the DEX Screener API key from environment variables."""
        return os.getenv("DEXSCREENER_API_KEY")

    @lru_cache(maxsize=1)
    def get_jupiter_api_url(self) -> str:
        """Get the Jupiter API URL from environment variables with a default fallback."""
        return os.getenv("JUPITER_API_URL", "https://quote-api.jup.ag/v6")  # Jupiter API default

    @lru_cache(maxsize=1)
    def get_log_level(self) -> str:
        """Get the logging level from environment variables with a default fallback."""
        return os.getenv("LOG_LEVEL", "INFO").upper()  # Default to INFO level

    @lru_cache(maxsize=1)
    def get_sleep_interval(self) -> int:
        """Get the sleep interval between trading cycles from environment variables with a default fallback."""
        return int(os.getenv("SLEEP_INTERVAL", 60))  # Default to 60 seconds


# Usage
config = Config()

# Example usage
if __name__ == '__main__':
    print(f"Wallet Private Key: {config.get_wallet_private_key()}")
    print(f"Slippage Tolerance: {config.get_slippage_tolerance()}")
    print(f"Profit Threshold: {config.get_profit_threshold_normal()}")
    print(f"Stop-Loss Percentage: {config.get_stop_loss_percentage()}")
    print(f"Initial Investment (USD): {config.get_initial_investment_usd()}")
    print(f"DEX Screener API Key: {config.get_dexscreener_api_key()}")
    print(f"Jupiter API URL: {config.get_jupiter_api_url()}")
    print(f"Log Level: {config.get_log_level()}")
    print(f"Sleep Interval: {config.get_sleep_interval()} seconds")