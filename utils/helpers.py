from solana.publickey import PublicKey
from solana.rpc.api import Client
import requests
from .logger import logger
from .config import config

def is_valid_solana_address(address: str) -> bool:
    """Basic check for a valid Solana address."""
    try:
        PublicKey(address)
        return True
    except Exception:
        return False

def get_solana_price_usd() -> float:
    """Fetches the current SOL price in USD from CoinGecko."""
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd")
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        return data["solana"]["usd"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching SOL price: {e}")
        return None

def check_enough_sol_balance(wallet_address: str, amount_needed: float) -> bool:
    """Checks if the wallet has enough SOL balance."""
    try:
        solana_client = Client("https://api.mainnet-beta.solana.com") # Consider your RPC endpoint
        balance = solana_client.get_balance(wallet_address).value / 10**9  # Lamports to SOL
        if balance >= amount_needed:
            return True
        else:
            logger.warning(f"Insufficient SOL balance. Needed: {amount_needed}, Available: {balance}")
            return False
    except Exception as e:
        logger.error(f"Error checking SOL balance: {e}")
        return False

# Example usage
if __name__ == '__main__':
    test_address = "So1111111111111111111111111111111111111112" #System Program Address
    is_valid = is_valid_solana_address(test_address)
    print(f"Is {test_address} a valid Solana address? {is_valid}")

    sol_price = get_solana_price_usd()
    print(f"Current SOL price: {sol_price}")

    # Replace with your actual wallet address
    my_wallet_address = "YOUR_WALLET_ADDRESS_HERE"
    amount_to_check = 0.1  # Example amount of SOL to check for
    has_enough = check_enough_sol_balance(my_wallet_address, amount_to_check)
    print(f"Enough SOL balance? {has_enough}")