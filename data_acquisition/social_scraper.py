import snscrape.modules.twitter as sntwitter
import praw  # Reddit API
from transformers import pipeline
from ..utils.logger import logger
import time
import random

class SocialScraper:
    def __init__(self):
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

    def scrape_twitter(self, query: str, num_tweets: int = 100, max_retries: int = 3) -> list:
        """Scrapes tweets from Twitter using snscrape with rate limiting and retries."""
        tweets = []
        for attempt in range(max_retries):
            try:
                for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
                    if i >= num_tweets:
                        break
                    tweets.append(tweet.content)
                    time.sleep(random.uniform(0.1, 0.5))  # Add random delay
                return tweets  # Return tweets if successful
            except Exception as e:
                logger.error(f"Error scraping Twitter (Attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(5 * (attempt + 1))  # Exponential backoff
        logger.error(f"Failed to scrape Twitter after {max_retries} attempts.")
        return []

    def scrape_reddit(self, subreddit: str, num_posts: int = 50, max_retries: int = 3) -> list:
        """Scrapes posts from a subreddit using PRAW with rate limiting and retries."""
        if not self.reddit:
            logger.warning("Reddit API not initialized. Skipping Reddit scraping.")
            return []
        posts = []
        for attempt in range(max_retries):
            try:
                for submission in self.reddit.subreddit(subreddit).hot(limit=num_posts):
                    posts.append(submission.title + "\n" + submission.selftext)
                    time.sleep(random.uniform(0.2, 0.8))  # Add random delay

                return posts  # Return posts if successful
            except Exception as e:
                logger.error(f"Error scraping Reddit (Attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(5 * (attempt + 1))  # Exponential backoff
        logger.error(f"Failed to scrape Reddit after {max_retries} attempts.")
        return []

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
        scores = []
        for text in text_list:
            try:
                sentiment = self.analyze_sentiment(text)
                if sentiment["label"] == "POSITIVE":
                    scores.append(sentiment["score"])
                else:
                    scores.append(1 - sentiment["score"])
            except Exception as e:
                logger.error(f"Error analyzing sentiment for a text: {e}")
                scores.append(0.5)  # Treat as neutral if analysis fails
        return sum(scores) / len(scores) if scores else 0.0