import time
import asyncio
import aiohttp
from typing import Optional, Dict, List
from functools import lru_cache
from datetime import datetime, timedelta

from ..utils.logger import logger
from ..utils.config import config


class PriceFetcher:
    def __init__(self):
        self.dexscreener_api_key = config.DEXSCREENER_API_KEY
        if not self.dexscreener_api_key:
            logger.warning("DEX Screener API key not found. Functionality will be limited.")

        # Rate limiting and caching
        self.last_api_call_time = datetime.now()
        self.api_call_interval = timedelta(seconds=1)  # Rate limit: 1 call per second
        self.price_cache: Dict[str, Tuple[Dict, datetime]] = {}  # token_address -> (price_data, timestamp)

    async def get_price_dexscreener(self, token_address: str, max_retries: int = 3, retry_delay: int = 2) -> Optional[Dict[str, float]]:
        """
        Gets real-time price data from Dexscreener with retry logic.
        """
        # Check cache first
        if token_address in self.price_cache:
            price_data, timestamp = self.price_cache[token_address]
            if datetime.now() - timestamp < timedelta(seconds=60):  # Cache TTL: 60 seconds
                return price_data

        for attempt in range(max_retries):
            try:
                # Rate limiting
                time_since_last_call = datetime.now() - self.last_api_call_time
                if time_since_last_call < self.api_call_interval:
                    await asyncio.sleep((self.api_call_interval - time_since_last_call).total_seconds())
                self.last_api_call_time = datetime.now()

                url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as response:
                        response.raise_for_status()
                        data = await response.json()

                        price_data = self._parse_price_data(data)
                        if price_data:
                            # Update cache
                            self.price_cache[token_address] = (price_data, datetime.now())
                            return price_data

                        logger.warning(f"Invalid data for {token_address} (attempt {attempt + 1}/{max_retries})")
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt + 1 < max_retries:
                    logger.warning(f"Request error: {e}. Retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(min(retry_delay, 10))
                    retry_delay *= 2
                else:
                    logger.error(f"Final failure fetching data for {token_address}: {e}")
                    break

        logger.error(f"Failed to get price data from Dexscreener for {token_address} after {max_retries} attempts.")
        return None

    async def get_prices_dexscreener_batch(self, token_addresses: List[str]) -> Dict[str, Dict]:
        """
        Fetches price data for multiple tokens in a single batch request.
        """
        # Rate limiting
        time_since_last_call = datetime.now() - self.last_api_call_time
        if time_since_last_call < self.api_call_interval:
            await asyncio.sleep((self.api_call_interval - time_since_last_call).total_seconds())
        self.last_api_call_time = datetime.now()

        try:
            url = "https://api.dexscreener.com/latest/dex/tokens"
            params = {"addresses": ",".join(token_addresses)}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()

                    prices = {}
                    for token_data in data.get("pairs", []):
                        token_address = token_data["baseToken"]["address"]
                        price_data = self._parse_price_data({"pairs": [token_data]})
                        if price_data:
                            prices[token_address] = price_data
                    return prices
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Error fetching batch price data: {e}")
            return {}

    def _parse_price_data(self, data: dict) -> Optional[Dict[str, float]]:
        """
        Parse the price data from the Dexscreener API response.
        """
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
        return None