import requests
from solana.rpc.api import Client
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from ..utils.logger import logger
from ..utils.config import config
from ..utils.helpers import check_enough_sol_balance
import base64
import time

class JupiterSwap:
    def __init__(self):
        self.private_key = config.WALLET_PRIVATE_KEY
        self.solana_client = Client("https://api.mainnet-beta.solana.com")  # Consider RPC endpoint
        self.slippage = config.SLIPPAGE_TOLERANCE or 0.5  # Default slippage tolerance
        self.jupiter_api_url = config.JUPITER_API_URL

    def _get_wallet_keypair(self) -> Keypair:
        """Fetch wallet keypair from private key."""
        return Keypair.from_base58_string(self.private_key)

    def _get_quote(self, input_mint: str, output_mint: str, amount: float) -> dict:
        """Fetch quote from Jupiter API."""
        try:
            url = f"{self.jupiter_api_url}/quote?inputMint={input_mint}&outputMint={output_mint}&amount={int(amount * 1e9)}&slippageBps={int(self.slippage * 10000)}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching Jupiter quote: {e}")
            return {}

    def _check_balance(self, wallet_address: str, amount: float) -> bool:
        """Check if wallet has enough SOL balance for the swap."""
        return check_enough_sol_balance(wallet_address, amount)

    def swap(self, input_mint: str, output_mint: str, amount: float, max_retries: int = 3) -> str:
        """Executes a token swap using Jupiter with retry logic."""
        wallet_keypair = self._get_wallet_keypair()
        wallet_address = str(wallet_keypair.pubkey())

        if not self._check_balance(wallet_address, amount):
            logger.error("Insufficient SOL balance.")
            return None

        for attempt in range(max_retries):
            try:
                # Step 1: Get Route
                route_data = self._get_quote(input_mint, output_mint, amount)
                if not route_data.get("data"):
                    logger.error(f"No swap route found (Attempt {attempt + 1}/{max_retries}).")
                    return None

                # Step 2: Prepare Transaction
                swap_transaction = route_data["data"][0]["swapTransaction"]
                transaction = Transaction.from_bytes(base64.b64decode(swap_transaction))

                # Step 3: Sign and Send Transaction
                transaction.sign(wallet_keypair)
                tx_signature = self.solana_client.send_raw_transaction(transaction.to_bytes())
                logger.info(f"Swap executed. Transaction signature: {tx_signature}")
                return tx_signature

            except Exception as e:
                logger.error(f"Error executing swap (Attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(2 * (attempt + 1))  # Exponential backoff

        logger.error(f"Failed to swap {input_mint} to {output_mint} after {max_retries} attempts.")
        return None