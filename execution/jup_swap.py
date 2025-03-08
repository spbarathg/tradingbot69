import asyncio
import aiohttp
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from ..utils.logger import logger
from ..utils.config import config
from ..utils.helpers import check_enough_sol_balance
import base64
import time
from typing import Optional, Dict


class JupiterSwap:
    def __init__(self):
        self.private_key = config.WALLET_PRIVATE_KEY
        self.solana_client = AsyncClient("https://api.mainnet-beta.solana.com")  # Use async client
        self.slippage = config.SLIPPAGE_TOLERANCE or 0.5  # Default slippage tolerance
        self.jupiter_api_url = config.JUPITER_API_URL
        self.max_retries = 3  # Maximum number of retries for swap attempts
        self.retry_delay = 2  # Initial delay between retries in seconds

        # Rate limiting and caching
        self.last_api_call_time = time.time()
        self.api_call_interval = 1  # Rate limit: 1 call per second
        self.quote_cache: Dict[str, Dict] = {}  # Cache for quotes

    def _get_wallet_keypair(self) -> Keypair:
        """Fetch wallet keypair from private key."""
        return Keypair.from_base58_string(self.private_key)

    async def _get_quote(self, input_mint: str, output_mint: str, amount: float) -> Optional[Dict]:
        """Fetch quote from Jupiter API with rate limiting and caching."""
        cache_key = f"{input_mint}_{output_mint}_{amount}"
        if cache_key in self.quote_cache:
            return self.quote_cache[cache_key]

        # Rate limiting
        time_since_last_call = time.time() - self.last_api_call_time
        if time_since_last_call < self.api_call_interval:
            await asyncio.sleep(self.api_call_interval - time_since_last_call)
        self.last_api_call_time = time.time()

        try:
            url = f"{self.jupiter_api_url}/quote?inputMint={input_mint}&outputMint={output_mint}&amount={int(amount * 1e9)}&slippageBps={int(self.slippage * 10000)}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()
                    self.quote_cache[cache_key] = data  # Cache the result
                    return data
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Error fetching Jupiter quote: {e}")
            return None

    async def _check_balance(self, wallet_address: str, amount: float) -> bool:
        """Check if wallet has enough SOL balance for the swap."""
        return check_enough_sol_balance(wallet_address, amount)

    async def swap(self, input_mint: str, output_mint: str, amount: float) -> Optional[str]:
        """Executes a token swap using Jupiter with retry logic."""
        wallet_keypair = self._get_wallet_keypair()
        wallet_address = str(wallet_keypair.pubkey())

        if not await self._check_balance(wallet_address, amount):
            logger.error("Insufficient SOL balance.")
            return None

        for attempt in range(self.max_retries):
            try:
                # Step 1: Get Route
                route_data = await self._get_quote(input_mint, output_mint, amount)
                if not route_data or not route_data.get("data"):
                    logger.error(f"No swap route found (Attempt {attempt + 1}/{self.max_retries}).")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                    continue

                # Step 2: Prepare Transaction
                swap_transaction = route_data["data"][0]["swapTransaction"]
                transaction = Transaction.from_bytes(base64.b64decode(swap_transaction))

                # Step 3: Sign and Send Transaction
                transaction.sign(wallet_keypair)
                tx_signature = await self.solana_client.send_raw_transaction(transaction.to_bytes())
                logger.info(f"Swap executed. Transaction signature: {tx_signature}")
                return tx_signature

            except Exception as e:
                logger.error(f"Error executing swap (Attempt {attempt + 1}/{self.max_retries}): {e}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff

        logger.error(f"Failed to swap {input_mint} to {output_mint} after {self.max_retries} attempts.")
        return None