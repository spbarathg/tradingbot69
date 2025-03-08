import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from functools import lru_cache

from ..data_acquisition.social_scraper import SocialScraper
from ..data_acquisition.realtime_prices import PriceFetcher
from ..utils.logger import logger


class SurgeDetector:
    def __init__(self, surge_volume_threshold: int = 200, surge_sentiment_threshold: float = 0.7):
        self.social_scraper = SocialScraper()
        self.price_fetcher = PriceFetcher()
        self.surge_volume_threshold = surge_volume_threshold
        self.surge_sentiment_threshold = surge_sentiment_threshold

        # Rate limiting and caching
        self.last_api_call_time = datetime.now()
        self.api_call_interval = timedelta(seconds=1)  # Rate limit: 1 call per second
        self.price_cache: Dict[str, Tuple[Dict, datetime]] = {}  # token_address -> (price_data, timestamp)
        self.social_cache: Dict[str, Tuple[List[str], datetime]] = {}  # token_address -> (tweets, timestamp)

    @lru_cache(maxsize=128)
    async def fetch_price_data(self, token_address: str) -> Optional[Dict]:
        """Fetches real-time price data for the token with caching."""
        if token_address in self.price_cache:
            price_data, timestamp = self.price_cache[token_address]
            if datetime.now() - timestamp < timedelta(seconds=60):  # Cache TTL: 60 seconds
                return price_data

        # Rate limiting
        time_since_last_call = datetime.now() - self.last_api_call_time
        if time_since_last_call < self.api_call_interval:
            await asyncio.sleep((self.api_call_interval - time_since_last_call).total_seconds())
        self.last_api_call_time = datetime.now()

        price_data = await self.price_fetcher.get_price_dexscreener(token_address)
        if not price_data:
            logger.warning(f"Price data not available for {token_address}.")
            return None

        # Update cache
        self.price_cache[token_address] = (price_data, datetime.now())
        return price_data

    @lru_cache(maxsize=128)
    async def fetch_social_data(self, token_symbol: str, token_address: str, num_tweets: int = 150) -> List[str]:
        """Scrapes social media data for the token with caching."""
        cache_key = f"{token_symbol}_{token_address}"
        if cache_key in self.social_cache:
            tweets, timestamp = self.social_cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=60):  # Cache TTL: 60 seconds
                return tweets

        # Rate limiting
        time_since_last_call = datetime.now() - self.last_api_call_time
        if time_since_last_call < self.api_call_interval:
            await asyncio.sleep((self.api_call_interval - time_since_last_call).total_seconds())
        self.last_api_call_time = datetime.now()

        query = f"{token_symbol} OR {token_address}"
        tweets = await self.social_scraper.scrape_twitter(query, num_tweets=num_tweets)
        if not tweets:
            logger.info(f"No social data found for {token_symbol} ({token_address}).")
            return []

        # Update cache
        self.social_cache[cache_key] = (tweets, datetime.now())
        return tweets

    async def analyze_social_sentiment(self, tweets: List[str]) -> float:
        """Analyzes the sentiment of scraped social media data."""
        if not tweets:
            return 0.0
        return await self.social_scraper.get_overall_sentiment(tweets)

    async def detect_surge_potential(self, token_address: str) -> bool:
        """Detects the potential for a token price surge based on social and market data."""
        try:
            price_data = await self.fetch_price_data(token_address)
            if not price_data:
                return False

            token_symbol = price_data["base_token_symbol"]
            tweets = await self.fetch_social_data(token_symbol, token_address)

            if not tweets:
                return False

            overall_sentiment = await self.analyze_social_sentiment(tweets)
            tweet_count = len(tweets)

            logger.info(f"Surge Detection: {token_symbol} | Tweets: {tweet_count} | Sentiment: {overall_sentiment}")

            # Surge detection criteria
            if tweet_count >= self.surge_volume_threshold and overall_sentiment >= self.surge_sentiment_threshold:
                logger.info(f"Surge potential detected for {token_address}.")
                return True

            logger.info(f"No surge potential for {token_address}.")
            return False

        except Exception as e:
            logger.error(f"Error detecting surge potential for {token_address}: {e}")
            return False


# Example Usage
async def main():
    surge_detector = SurgeDetector(surge_volume_threshold=250, surge_sentiment_threshold=0.75)
    token_address = "EjmcZ9EcE6JMRyASG4sJ49tfzdR16gJ1eQGm2UjGVkJ"  # Replace with real token address
    if await surge_detector.detect_surge_potential(token_address):
        print(f"Surge potential detected for {token_address}!")
    else:
        print(f"No surge potential for {token_address}.")


if __name__ == '__main__':
    asyncio.run(main())