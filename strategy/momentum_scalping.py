import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from functools import lru_cache

import talib  # Import TA-Lib for technical analysis
from ..data_acquisition.realtime_prices import PriceFetcher
from ..data_acquisition.social_scraper import SocialScraper
from ..utils.logger import logger
from ..utils.config import config


class MomentumScalper:
    def __init__(self):
        self.price_fetcher = PriceFetcher()
        self.social_scraper = SocialScraper()
        self.profit_threshold_normal = config.PROFIT_THRESHOLD_NORMAL
        self.jupiter_api_url = config.JUPITER_API_URL  # Use Jupiter API URL from config

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
    async def fetch_social_data(self, token_symbol: str, token_address: str, num_tweets: int = 50) -> List[str]:
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

    async def check_buy_signal(self, token_address: str, social_volume_threshold: int = 5, sentiment_threshold: float = 0.6) -> bool:
        """
        Checks for a buy signal based on price momentum, social volume, and sentiment.
        
        Args:
            token_address (str): The token address.
            social_volume_threshold (int): Minimum number of social mentions for a buy signal.
            sentiment_threshold (float): Minimum sentiment score (0 to 1) for a buy signal.
        
        Returns:
            bool: True if a buy signal is detected, False otherwise.
        """
        try:
            price_data = await self.fetch_price_data(token_address)
            if not price_data:
                logger.warning(f"No price data available for {token_address}. Skipping buy signal check.")
                return False

            # Fetch the current price
            current_price = price_data["price_usd"]

            # Social volume and sentiment check
            token_symbol = price_data["base_token_symbol"]
            tweets = await self.fetch_social_data(token_symbol, token_address)
            if tweets:
                overall_sentiment = await self.social_scraper.get_overall_sentiment(tweets)
                logger.info(f"Sentiment Score: {overall_sentiment}, Sentiment Threshold: {sentiment_threshold}")
                if len(tweets) >= social_volume_threshold and overall_sentiment >= sentiment_threshold:
                    logger.info(f"Buy signal detected for {token_address}: Positive sentiment and sufficient social volume.")
                    return True
                else:
                    logger.info(f"No buy signal: Insufficient social volume or negative sentiment.")
                    return False
            else:
                logger.info("No tweets found for token. Skipping social volume/sentiment check.")
                return False

        except Exception as e:
            logger.error(f"Error checking buy signal for {token_address}: {e}")
            return False

    def check_sell_signal(self, entry_price: float, current_price: float, surge_potential: bool = False) -> bool:
        """
        Checks for a sell signal based on profit threshold and surge potential.
        
        Args:
            entry_price (float): The price at which the token was bought.
            current_price (float): The current price of the token.
            surge_potential (bool): Whether surge potential has been detected.
        
        Returns:
            bool: True if a sell signal is detected, False otherwise.
        """
        try:
            profit = (current_price - entry_price) / entry_price
            logger.info(f"Current Profit: {profit}, Normal Threshold: {self.profit_threshold_normal}")

            if surge_potential:
                logger.info(f"Surge potential detected. Holding token for now...")
                return False  # Hold if surge potential is detected
            elif profit >= self.profit_threshold_normal:
                logger.info("Sell signal triggered: Profit threshold reached.")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Error checking sell signal: {e}")
            return False

    async def get_historical_price(self, token_address: str, time_ago: str) -> Optional[Dict]:
        """
        Fetches historical price data. Placeholder implementation for now.
        """
        # To be implemented with a proper historical price API integration.
        logger.info(f"Fetching historical price for {token_address}, {time_ago} ago.")
        return None

    def calculate_atr_stop_loss(self, historical_prices: Dict[str, List[float]], current_price: float, atr_period: int = 14, atr_multiplier: int = 2) -> Optional[float]:
        """
        Calculates a dynamic stop-loss based on Average True Range (ATR).
        
        Args:
            historical_prices (dict): Dictionary of high, low, and close prices.
            current_price (float): The current price of the token.
            atr_period (int): Period for ATR calculation (default: 14).
            atr_multiplier (int): Multiplier for ATR to set stop-loss (default: 2).
        
        Returns:
            float: Calculated stop-loss price.
        """
        try:
            atr = talib.ATR(historical_prices['high'], historical_prices['low'], historical_prices['close'], timeperiod=atr_period)[-1]
            stop_loss = current_price - (atr_multiplier * atr)
            return stop_loss

        except Exception as e:
            logger.error(f"Error calculating ATR stop loss: {e}")
            return None


# Example usage
async def main():
    scalper = MomentumScalper()
    token_address = "EjmcZ9EcE6JMRyASG4sJ49tfzdR16gJ1eQGm2UjGVkJ"  # Replace with a real token address

    # Check Buy Signal
    buy_signal = await scalper.check_buy_signal(token_address)
    if buy_signal:
        print(f"Buy signal detected for {token_address}")
    else:
        print(f"No buy signal detected for {token_address}")

    # Check Sell Signal
    entry_price = 0.001  # Replace with your actual entry price
    current_price = 0.0015  # Replace with your current price
    sell_signal = scalper.check_sell_signal(entry_price, current_price)

    if sell_signal:
        print("Sell signal detected.")
    else:
        print("No sell signal detected.")


if __name__ == '__main__':
    asyncio.run(main())