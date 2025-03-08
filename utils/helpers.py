import asyncio
from typing import Optional
from datetime import datetime, timedelta
from functools import lru_cache

from solana.publickey import PublicKey
from solana.rpc.async_api import AsyncClient
import aiohttp
from ..logger import logger
from ..config import config


def is_valid_solana_address(address: str) -> bool:
    """Checks if the given address is a valid Solana public key."""
    try:
        PublicKey(address)
        return True
    except Exception:
        logger.warning(f"Invalid Solana address: {address}")
        return False


@lru_cache(maxsize=1)
async def get_solana_price_usd() -> Optional[float]:
    """Fetches the current SOL price in USD from CoinGecko with caching and rate limiting."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd") as response:
                response.raise_for_status()  # Raise error for bad responses
                data = await response.json()
                return data["solana"]["usd"]
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(f"Error fetching SOL price: {e}")
        return None


async def check_enough_sol_balance(wallet_address: str, amount_needed: float) -> bool:
    """Checks if the wallet has sufficient SOL balance."""
    try:
        async with AsyncClient("https://api.mainnet-beta.solana.com") as client:
            balance_lamports = (await client.get_balance(wallet_address))["result"]["value"]
            balance_sol = balance_lamports / 10**9  # Convert lamports to SOL
            if balance_sol >= amount_needed:
                return True
            else:
                logger.warning(f"Insufficient SOL: Needed {amount_needed}, Available {balance_sol}")
                return False
    except Exception as e:
        logger.error(f"Error checking SOL balance for {wallet_address}: {e}")
        return False


# Example usage
async def main():
    test_address = "So1111111111111111111111111111111111111112"  # System Program Address
    is_valid = is_valid_solana_address(test_address)
    print(f"Is {test_address} a valid Solana address? {is_valid}")

    sol_price = await get_solana_price_usd()
    print(f"Current SOL price: {sol_price}")

    my_wallet_address = "YOUR_WALLET_ADDRESS_HERE"
    amount_to_check = 0.1  # Example amount in SOL
    has_enough = await check_enough_sol_balance(my_wallet_address, amount_to_check)
    print(f"Enough SOL balance? {has_enough}")


if __name__ == '__main__':
    asyncio.run(main())