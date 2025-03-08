import requests
import json
from . import social_scraper
from ..utils.logger import logger
from ..utils.config import config

class PriceFetcher:
    def __init__(self):
        self.dexscreener_api_key = config.DEXSCREENER_API_KEY
        if not self.dexscreener_api_key:
            logger.warning("DEX Screener API key not found.  Functionality will be limited.")

    def get_price_dexscreener(self, token_address: str) -> dict:
        """
        Gets real-time price data from Dexscreener.
        """
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            response = requests.get(url)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            if data.get("pairs"):
                #For simplicity, we'll just get the first pair (assuming it's the most liquid)
                pair = data["pairs"][0]
                price_data = {
                    "price_usd": float(pair["priceUsd"]),
                    "base_token_symbol": pair["baseToken"]["symbol"],
                    "quote_token_symbol": pair["quoteToken"]["symbol"],
                    "volume_24h": float(pair["volume"]["h24"]),
                    "liquidity_usd": float(pair["liquidity"]["usd"])
                }
                return price_data
            else:
                logger.warning(f"No pairs found for token address: {token_address}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from Dexscreener: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Dexscreener response: {e}")
            return None
    def get_jupiter_liquidity(self, token_mint: str):
        """
        Fetch liquidity information from Jupiter.
        """
        try:
            # Construct the request URL for the Jupiter price data API.
            # Ensure you replace 'YOUR_MINT_ADDRESS' with the actual mint address of the token.
            url = f"https://quote-api.jup.ag/v6/price?ids={token_mint}"

            # Make the HTTP GET request to the Jupiter API.
            response = requests.get(url)

            # If the request was successful (status code 200), process the data.
            if response.status_code == 200:
                data = response.json()

                # Check if the data contains the expected information for the token.
                if token_mint in data:
                    # Extract the price from the response data.
                    price = data[token_mint]["price"]
                    return price
                else:
                    logger.warning(f"Token {token_mint} not found in Jupiter API response.")
                    return None
            else:
                # Log an error if the request was unsuccessful.
                logger.error(f"Failed to fetch price from Jupiter API. Status code: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            # Handle any request-related errors, such as network issues.
            logger.error(f"Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            # Handle JSON decoding errors if the response is not in the expected format.
            logger.error(f"Failed to decode JSON response: {e}")
            return None
        except KeyError as e:
            # Handle KeyError if the expected keys are not found in the dictionary.
            logger.error(f"KeyError: {e}")
            return None

# Example Usage (inside realtime_prices.py or in a separate test script)
if __name__ == '__main__':
    price_fetcher = PriceFetcher()
    # Replace with a real token address
    token_address = "EjmcZ9EcE6JMRyASG4sJ49tfzdR16gJ1eQGm2UjGVkJ" #Example token address
    price_data = price_fetcher.get_price_dexscreener(token_address)

    if price_data:
        print(f"Token: {price_data['base_token_symbol']}")
        print(f"Price (USD): {price_data['price_usd']}")
        print(f"24h Volume: {price_data['volume_24h']}")
        print(f"Liquidity (USD): {price_data['liquidity_usd']}")
    else:
        print("Could not retrieve price data.")