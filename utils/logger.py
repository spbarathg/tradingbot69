import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional, Union


def setup_logger(
    name: str = __name__,
    level: Union[int, str] = logging.INFO,
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 3,
    format: str = "%(asctime)s - %(levelname)s - %(message)s",
    datefmt: str = "%Y-%m-%d %H:%M:%S",
) -> logging.Logger:
    """
    Configures and returns a logger with flexible settings.

    Args:
        name (str): Name of the logger. Defaults to the module name.
        level (Union[int, str]): Logging level (e.g., logging.INFO, "DEBUG"). Defaults to logging.INFO.
        log_file (Optional[str]): Path to the log file. If None, logs are only written to the console.
        max_file_size (int): Maximum size of each log file in bytes. Defaults to 10 MB.
        backup_count (int): Number of backup log files to keep. Defaults to 3.
        format (str): Log message format. Defaults to "%(asctime)s - %(levelname)s - %(message)s".
        datefmt (str): Date format for log messages. Defaults to "%Y-%m-%d %H:%M:%S".

    Returns:
        logging.Logger: Configured logger instance.
    """
    # Convert string log level to logging level
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())

    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicate logs
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create a formatter
    formatter = logging.Formatter(format, datefmt=datefmt)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add file handler if log_file is provided
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Example usage
if __name__ == "__main__":
    # Set up logger with console and file output
    logger = setup_logger(
        name="TradingBot",
        level="DEBUG",  # Use string log level
        log_file="trading_bot.log",  # Log to a file
        max_file_size=5 * 1024 * 1024,  # 5 MB per log file
        backup_count=2,  # Keep 2 backup log files
    )

    # Log messages
    logger.debug("This is a debug message.")
    logger.info("Bot started.")
    logger.warning("Something might be wrong.")
    logger.error("An error occurred.")
    logger.critical("A critical error occurred!")