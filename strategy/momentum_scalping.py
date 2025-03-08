from ..data_acquisition.realtime_prices import PriceFetcher
from ..data_acquisition.social_scraper import SocialScraper
from ..utils.logger import logger
from ..utils.config import config

class MomentumScalper:
    def __init__(self):
        self.price_fetcher = PriceFetcher()
        self.social_scraper = SocialScraper()
        self.profit_threshold_normal = config.PROFIT_THRESHOLD_NORMAL
        self.jupiter_api_url = config.JUPITER_API_URL # Use Jupiter API URL from config


    def check_buy_signal(self, token_address: str, social_volume_threshold: int = 5, sentiment_threshold: float = 0.6) -> bool:
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
            price_data = self.price_fetcher.get_price_dexscreener(token_address)

            if not price_data:
                logger.warning(f"No price data available for {token_address}.  Skipping buy signal check.")
                return False

            # Basic momentum check (e.g., price increase in the last few minutes)
            # This is a simplified example.  You'll likely want to use more sophisticated
            # momentum indicators (RSI, MACD, etc.).
            current_price = price_data["price_usd"]
            #historical_price = self.get_historical_price(token_address, time_ago="5m")  # Implement this!

            # if historical_price and current_price > historical_price:
            #     logger.info(f"Price increased. Current Price: {current_price}, Historical Price: {historical_price}")
            # else:
            #     logger.info("No price increase detected based on historical price");
            #     return False

            # Social volume and sentiment check
            twitter_query = f"{price_data['base_token_symbol']} OR {token_address}"
            tweets = self.social_scraper.scrape_twitter(twitter_query, num_tweets=50)  # Adjust num_tweets as needed
            if tweets:
                overall_sentiment = self.social_scraper.get_overall_sentiment(tweets)
                logger.info(f"Sentiment Score {overall_sentiment} and Sentiment Threshold {sentiment_threshold}")
                if len(tweets) >= social_volume_threshold and overall_sentiment >= sentiment_threshold:
                    logger.info(f"Buy signal detected for {token_address}: Price momentum, social volume, and positive sentiment.")
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
        profit = (current_price - entry_price) / entry_price
        logger.info(f"Current Profit {profit} and Normal Threshold {self.profit_threshold_normal}")

        if surge_potential:
            #Implement phased withdrawal strategy in the future.
            logger.info(f"Surge potential detected. Holding token for now...")
            return False  # Hold if surge potential is detected
        elif profit >= self.profit_threshold_normal:
            logger.info(f"Sell signal triggered: Profit threshold reached.")
            return True
        else:
            return False

    def get_historical_price(self, token_address: str, time_ago: str):
        """
        This method can fetch historical data with the time ago parameter if needed.
        """
        #Place holder since the current implementation needs the historical price to fully function
        return None


# Example usage
if __name__ == '__main__':
    scalper = MomentumScalper()
    token_address = "EjmcZ9EcE6JMRyASG4sJ49tfzdR16gJ1eQGm2UjGVkJ"  # Replace with a real token address
    buy_signal = scalper.check_buy_signal(token_address)
    if buy_signal:
        print(f"Buy signal detected for {token_address}")
    else:
        print(f"No buy signal detected for {token_address}")
    entry_price = 0.001  # Replace with your actual entry price
    current_price = 0.0015 #Replace with your current price
    sell_signal = scalper.check_sell_signal(entry_price, current_price)

    if sell_signal:
        print("Sell signal detected.")
    else:
        print("No sell signal detected.")