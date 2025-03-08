import asyncio
import os
import random
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

import snscrape.modules.twitter as sntwitter
import praw
from transformers import pipeline
from ..utils.logger import logger


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

        # Rate limiting and caching
        self.last_twitter_call_time = datetime.now()
        self.twitter_call_interval = timedelta(seconds=1)  # Rate limit: 1 call per second
        self.last_reddit_call_time = datetime.now()
        self.reddit_call_interval = timedelta(seconds=1)  # Rate limit: 1 call per second
        self.scraped_data_cache: Dict[str, Tuple[List[str], datetime]] = {}  # query/subreddit -> (data, timestamp)
        self.cache_ttl = timedelta(seconds=60)  # Cache TTL: 60 seconds

    async def scrape_twitter(self, query: str, num_tweets: int = 100, max_retries: int = 3) -> List[str]:
        """Scrapes tweets from Twitter using snscrape with rate limiting and retries."""
        # Check cache first
        if query in self.scraped_data_cache:
            tweets, timestamp = self.scraped_data_cache[query]
            if datetime.now() - timestamp < self.cache_ttl:
                return tweets

        for attempt in range(max_retries):
            try:
                # Rate limiting
                await self._enforce_rate_limit("twitter")

                # Use asyncio.to_thread to run synchronous snscrape in a separate thread
                tweets = await asyncio.to_thread(
                    lambda: [
                        tweet.content for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items())
                        if i < num_tweets
                    ]
                )
                # Update cache
                self.scraped_data_cache[query] = (tweets, datetime.now())
                return tweets
            except Exception as e:
                logger.error(f"Error scraping Twitter (Attempt {attempt + 1}/{max_retries}): {e}")
                await asyncio.sleep(5 * (attempt + 1))  # Exponential backoff
        logger.error(f"Failed to scrape Twitter after {max_retries} attempts.")
        return []

    async def scrape_reddit(self, subreddit: str, num_posts: int = 50, max_retries: int = 3) -> List[str]:
        """Scrapes posts from a subreddit using PRAW with rate limiting and retries."""
        if not self.reddit:
            logger.warning("Reddit API not initialized. Skipping Reddit scraping.")
            return []

        # Check cache first
        if subreddit in self.scraped_data_cache:
            posts, timestamp = self.scraped_data_cache[subreddit]
            if datetime.now() - timestamp < self.cache_ttl:
                return posts

        for attempt in range(max_retries):
            try:
                # Rate limiting
                await self._enforce_rate_limit("reddit")

                # Use asyncio.to_thread to run synchronous PRAW in a separate thread
                posts = await asyncio.to_thread(
                    lambda: [
                        submission.title + "\n" + submission.selftext
                        for submission in self.reddit.subreddit(subreddit).hot(limit=num_posts)
                    ]
                )
                # Update cache
                self.scraped_data_cache[subreddit] = (posts, datetime.now())
                return posts
            except Exception as e:
                logger.error(f"Error scraping Reddit (Attempt {attempt + 1}/{max_retries}): {e}")
                await asyncio.sleep(5 * (attempt + 1))  # Exponential backoff
        logger.error(f"Failed to scrape Reddit after {max_retries} attempts.")
        return []

    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyzes the sentiment of a given text using a transformer model."""
        try:
            result = self.sentiment_pipeline(text)[0]
            return result
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {"label": "NEUTRAL", "score": 0.5}

    def get_overall_sentiment(self, text_list: List[str]) -> float:
        """Calculates an overall sentiment score from a list of texts."""
        if not text_list:
            return 0.0
        try:
            # Process sentiment analysis in batches to improve efficiency
            batch_size = 32  # Adjust based on model and hardware capabilities
            scores = []
            for i in range(0, len(text_list), batch_size):
                batch = text_list[i:i + batch_size]
                sentiment_results = self.sentiment_pipeline(batch)
                scores.extend([
                    result["score"] if result["label"] == "POSITIVE" else 1 - result["score"]
                    for result in sentiment_results
                ])
            return sum(scores) / len(scores)
        except Exception as e:
            logger.error(f"Error analyzing batch sentiment: {e}")
            return 0.0

    async def _enforce_rate_limit(self, platform: str) -> None:
        """
        Ensures API calls respect the rate limit for the specified platform.
        """
        if platform == "twitter":
            time_since_last_call = datetime.now() - self.last_twitter_call_time
            if time_since_last_call < self.twitter_call_interval:
                await asyncio.sleep((self.twitter_call_interval - time_since_last_call).total_seconds())
            self.last_twitter_call_time = datetime.now()
        elif platform == "reddit":
            time_since_last_call = datetime.now() - self.last_reddit_call_time
            if time_since_last_call < self.reddit_call_interval:
                await asyncio.sleep((self.reddit_call_interval - time_since_last_call).total_seconds())
            self.last_reddit_call_time = datetime.now()