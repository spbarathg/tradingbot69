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
                response = requests.get(url, timeout=10)  # Add a timeout
                response.raise_for_status()  # Raise HTTPError for bad responses

                data = response.json()

                if data.get("pairs"):
                    pair = data["pairs"][0]
                    price_data = {
                        "price_usd": float(pair["priceUsd"]),
                        "base_token_symbol": pair["baseToken"]["symbol"],
                        "quote_token_symbol": pair["quoteToken"]["symbol"],
                        "volume_24h": float(pair["volume"]["h24"]),
                        "liquidity_usd": float(pair["liquidity"]["usd"])
                    }
                    # Add data validation here
                    if price_data["price_usd"] <= 0 or price_data["liquidity_usd"] <=0:
                        logger.warning(f"Invalid data from Dexscreener. Price or Liquidity <= 0")
                        return None
                    return price_data
                else:
                    logger.warning(f"No pairs found for token address: {token_address}")
                    return None

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    logger.warning(f"Dexscreener API rate limit exceeded for {token_address} (Attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds.")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"HTTP error fetching data from Dexscreener for {token_address}: {e}")
                    return None
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching data from Dexscreener for {token_address}: {e}")
                return None
            except (KeyError, ValueError) as e:
                logger.error(f"Error parsing Dexscreener response for {token_address}: {e}")
                return None

        logger.error(f"Failed to get price data from Dexscreener for {token_address} after {max_retries} attempts.")
        return None

    # Add similar error handling and retry logic to get_jupiter_liquidity