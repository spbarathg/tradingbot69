from ..data_acquisition.social_scraper import SocialScraper
from ..data_acquisition.realtime_prices import PriceFetcher
from ..utils.logger import logger

class SurgeDetector:
    def __init__(self, surge_volume_threshold=200, surge_sentiment_threshold=0.7):
        self.social_scraper = SocialScraper()
        self.price_fetcher = PriceFetcher()
        self.surge_volume_threshold = surge_volume_threshold
        self.surge_sentiment_threshold = surge_sentiment_threshold

    def fetch_price_data(self, token_address: str) -> dict:
        """Fetches real-time price data for the token."""
        price_data = self.price_fetcher.get_price_dexscreener(token_address)
        if not price_data:
            logger.warning(f"Price data not available for {token_address}.")
            return None
        return price_data

    def fetch_social_data(self, token_symbol: str, token_address: str, num_tweets: int = 150) -> list:
        """Scrapes social media data for the token."""
        query = f"{token_symbol} OR {token_address}"
        tweets = self.social_scraper.scrape_twitter(query, num_tweets=num_tweets)
        if not tweets:
            logger.info(f"No social data found for {token_symbol} ({token_address}).")
        return tweets

    def analyze_social_sentiment(self, tweets: list) -> float:
        """Analyzes the sentiment of scraped social media data."""
        if not tweets:
            return 0.0
        return self.social_scraper.get_overall_sentiment(tweets)

    def detect_surge_potential(self, token_address: str) -> bool:
        """Detects the potential for a token price surge based on social and market data."""
        try:
            price_data = self.fetch_price_data(token_address)
            if not price_data:
                return False

            token_symbol = price_data["base_token_symbol"]
            tweets = self.fetch_social_data(token_symbol, token_address)

            if not tweets:
                return False

            overall_sentiment = self.analyze_social_sentiment(tweets)
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
if __name__ == '__main__':
    surge_detector = SurgeDetector(surge_volume_threshold=250, surge_sentiment_threshold=0.75)
    token_address = "EjmcZ9EcE6JMRyASG4sJ49tfzdR16gJ1eQGm2UjGVkJ"  # Replace with real token address
    if surge_detector.detect_surge_potential(token_address):
        print(f"Surge potential detected for {token_address}!")
    else:
        print(f"No surge potential for {token_address}.")