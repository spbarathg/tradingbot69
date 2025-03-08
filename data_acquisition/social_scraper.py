import snscrape.modules.twitter as sntwitter
import praw  # Reddit API
from transformers import pipeline
from ..utils.logger import logger
import os

class SocialScraper:
    def __init__(self):
        # Sentiment analysis pipeline
        self.sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.reddit_user_agent = os.getenv("REDDIT_USER_AGENT")
        if not all([self.reddit_client_id, self.reddit_client_secret, self.reddit_user_agent]):
            logger.warning("Reddit API credentials not found. Reddit scraping will be disabled.")
            self.reddit = None
        else:
            try:
                self.reddit = praw.Reddit(
                    client_id=self.reddit_client_id,
                    client_secret=self.reddit_client_secret,
                    user_agent=self.reddit_user_agent,
                )
            except Exception as e:
                logger.error(f"Failed to connect to Reddit API: {e}")
                self.reddit = None

    def scrape_twitter(self, query: str, num_tweets: int = 100) -> list:
        """Scrapes tweets from Twitter using snscrape."""
        tweets = []
        try:
            for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
                if i >= num_tweets:
                    break
                tweets.append(tweet.content)
        except Exception as e:
            logger.error(f"Error scraping Twitter: {e}")
        return tweets

    def scrape_reddit(self, subreddit: str, num_posts: int = 50) -> list:
        """Scrapes posts from a subreddit using PRAW."""
        if not self.reddit:
            logger.warning("Reddit API not initialized. Skipping Reddit scraping.")
            return []
        posts = []
        try:
            for submission in self.reddit.subreddit(subreddit).hot(limit=num_posts):
                posts.append(submission.title + "\n" + submission.selftext)  # Combine title and body
        except Exception as e:
            logger.error(f"Error scraping Reddit: {e}")
        return posts

    def analyze_sentiment(self, text: str) -> dict:
        """Analyzes the sentiment of a given text using a transformer model."""
        try:
            result = self.sentiment_pipeline(text)[0]
            return result  # {'label': 'POSITIVE', 'score': 0.999...}
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {"label": "NEUTRAL", "score": 0.5} # Default neutral sentiment

    def get_overall_sentiment(self, text_list: list) -> float:
        """Calculates an overall sentiment score from a list of texts."""
        if not text_list:
            return 0.0  # Default neutral sentiment if no text is provided
        scores = [self.analyze_sentiment(text)["score"] if self.analyze_sentiment(text)["label"] == "POSITIVE" else (1 - self.analyze_sentiment(text)["score"]) for text in text_list]
        return sum(scores) / len(scores)

# Example usage (inside social_scraper.py or in a separate test script)
if __name__ == '__main__':
    scraper = SocialScraper()

    #Twitter Scraping and Sentiment Analysis
    twitter_query = "Solana meme coins"
    num_tweets = 20
    tweets = scraper.scrape_twitter(twitter_query, num_tweets)
    if tweets:
        overall_sentiment_twitter = scraper.get_overall_sentiment(tweets)
        print(f"Overall sentiment for Twitter query '{twitter_query}': {overall_sentiment_twitter}")
    else:
        print("Could not retrieve tweets.")

    #Reddit Scraping and Sentiment Analysis
    subreddit_name = "CryptoCurrency"
    num_posts = 10
    reddit_posts = scraper.scrape_reddit(subreddit_name, num_posts)
    if reddit_posts:
        overall_sentiment_reddit = scraper.get_overall_sentiment(reddit_posts)
        print(f"Overall sentiment for Reddit subreddit '{subreddit_name}': {overall_sentiment_reddit}")
    else:
        print("Could not retrieve Reddit posts.")