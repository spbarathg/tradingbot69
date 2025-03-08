from ..data_acquisition.social_scraper import SocialScraper
from ..data_acquisition.realtime_prices import PriceFetcher
from ..utils.logger import logger

class SurgeDetector:
    def __init__(self):
        self.social_scraper = SocialScraper()
        self.price_fetcher = PriceFetcher()
        self.surge_volume_threshold = 200 #Adjust based on observation
        self.surge_sentiment_threshold = 0.7 #Adjust based on observation

    def detect_surge_potential(self, token_address: str) -> bool:
        """
        Detects the potential for a price surge based on social media trends and sentiment.

        Args:
            token_address (str): The token address to analyze.

        Returns:
            bool: True if surge potential is detected, False otherwise.
        """
        try:
            price_data = self.price_fetcher.get_price_dexscreener(token_address)
            if not price_data:
                logger.warning(f"Could not retrieve price data for {token_address}.  Skipping surge detection.")
                return False
            token_symbol = price_data["base_token_symbol"]
            #Scrape Social Media Data
            query = f"{token_symbol} OR {token_address}"
            tweets = self.social_scraper.scrape_twitter(query, num_tweets=150)  # Adjust num_tweets as needed

            if not tweets:
                logger.info(f"No social media data found for {token_address}.  No surge detected.")
                return False

            #Analyze Social Sentiment and Volume
            overall_sentiment = self.social_scraper.get_overall_sentiment(tweets)
            tweet_count = len(tweets)
            logger.info(f"Surge Detection: Token {token_symbol}, Tweet Count: {tweet_count}, Sentiment: {overall_sentiment}")
            #Surge Detection Logic
            if tweet_count >= self.surge_volume_threshold and overall_sentiment >= self.surge_sentiment_threshold:
                logger.info(f"Surge potential detected for {token_address}!")
                return True
            else:
                logger.info(f"No surge potential detected for {token_address}.")
                return False

        except Exception as e:
            logger.error(f"Error detecting surge potential for {token_address}: {e}")
            return False

# Example Usage
if __name__ == '__main__':
    surge_detector = SurgeDetector()
    token_address = "EjmcZ9EcE6JMRyASG4sJ49tfzdR16gJ1eQGm2UjGVkJ"  # Replace with a real token address
    surge_potential = surge_detector.detect_surge_potential(token_address)

    if surge_potential:
        print(f"Surge potential detected for {token_address}!")
    else:
        print(f"No surge potential detected for {token_address}.")