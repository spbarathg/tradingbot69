from core.bot import TradingBot
from utils.logger import logger
import os

if __name__ == "__main__":
    try:
        # Replace with the token addresses you want to trade
        token_addresses = os.getenv("TOKENS_TO_TRADE", "So1111111111111111111111111111111111111112,EPjFWdd5AufqALUs2vW0ouAZnuuzqvTZcztBbuw61zPX").split(",")
        logger.info(f"Starting bot with token addresses: {token_addresses}")
        bot = TradingBot()
        bot.trade_loop(token_addresses)
    except Exception as e:
        logger.error(f"An error occurred during bot initialization: {e}")