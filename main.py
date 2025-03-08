import asyncio
import os
import signal
import sys
from typing import List

from core.bot import TradingBot
from utils.logger import logger


async def main():
    """Main function to initialize and run the trading bot."""
    try:
        # Fetch token addresses from environment variable or use defaults
        token_addresses = os.getenv(
            "TOKENS_TO_TRADE",
            "So1111111111111111111111111111111111111112,EPjFWdd5AufqALUs2vW0ouAZnuuzqvTZcztBbuw61zPX",
        ).split(",")

        logger.info(f"Starting bot with token addresses: {token_addresses}")

        # Initialize the trading bot
        bot = TradingBot()

        # Handle graceful shutdown
        def handle_shutdown(signal, frame):
            logger.info("Shutting down the bot gracefully...")
            asyncio.create_task(bot.shutdown())
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        # Start the trading loop
        await bot.trade_loop(token_addresses)

    except Exception as e:
        logger.error(f"Bot initialization error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())