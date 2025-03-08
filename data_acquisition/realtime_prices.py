import requests
import time
from ..utils.logger import logger
from ..utils.config import config

class PriceFetcher:
    def __init__(self):
        self.dexscreener_api_key = config.DEXSCREENER_API_KEY
        if not self.dexscreener_api_key:
            logger.warning("DEX Screener API key not found. Functionality will be limited.")

    def get_price_dexscreener(self, token_address: str, max_retries: int = 3, retry_delay: int = 2) -> dict:
        """
        Gets real-time price data from Dexscreener with retry logic.
        """
        for attempt in range(max_retries):
            try:
                url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                data = response.json()

                if data.get("pairs"):
                    pair = data["pairs"][0]
                    price_usd = float(pair["priceUsd"])
                    liquidity_usd = float(pair["liquidity"]["usd"])

                    if price_usd > 0 and liquidity_usd > 0:
                        return {
                            "price_usd": price_usd,
                            "base_token_symbol": pair["baseToken"]["symbol"],
                            "quote_token_symbol": pair["quoteToken"]["symbol"],
                            "volume_24h": float(pair["volume"]["h24"]),
                            "liquidity_usd": liquidity_usd
                        }

                logger.warning(f"Invalid data for {token_address} (attempt {attempt + 1}/{max_retries})")
            except requests.exceptions.RequestException as e:
                if attempt + 1 < max_retries:
                    logger.warning(f"Request error: {e}. Retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(min(retry_delay, 10))
                    retry_delay *= 2
                else:
                    logger.error(f"Final failure fetching data for {token_address}: {e}")
                    break

        logger.error(f"Failed to get price data from Dexscreener for {token_address} after {max_retries} attempts.")
        return None