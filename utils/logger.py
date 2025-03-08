import logging

# Configure logging with flexible settings
def setup_logger(name=__name__, level=logging.INFO):
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    
    return logger

# Example usage
logger = setup_logger()
logger.info("Bot started")
logger.warning("Something might be wrong")
logger.error("An error occurred")