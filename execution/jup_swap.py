import requests
from jupysdk.Slippage import Slippage
from solana.rpc.api import Client
from solana.publickey import PublicKey
from solana.transaction import Transaction
from solders.hash import Hash
from solders.keypair import Keypair
from ..utils.logger import logger
from ..utils.config import config
from ..utils.helpers import check_enough_sol_balance
import base64
import time

class JupiterSwap:
    def __init__(self):
        self.private_key = config.WALLET_PRIVATE_KEY
        self.solana_client = Client("https://api.mainnet-beta.solana.com") # Consider your RPC endpoint
        self.slippage = config.SLIPPAGE_TOLERANCE
        self.jupiter_api_url = config.JUPITER_API_URL  # From config

    def swap(self, input_mint: str, output_mint: str, amount: float, max_retries: int = 3) -> str:
        """
        Executes a swap using the Jupiter aggregator with retry logic.
        """
        for attempt in range(max_retries):
            try:
                wallet_keypair = Keypair.from_base58_string(self.private_key)
                wallet_address = str(wallet_keypair.pubkey())

                # Ensure wallet has enough balance
                has_enough_balance = check_enough_sol_balance(wallet_address, amount)
                if not has_enough_balance:
                    return None

                # Step 1: Get Route
                url = f"{self.jupiter_api_url}/quote?inputMint={input_mint}&outputMint={output_mint}&amount={amount * 10**9}&slippageBps={self.slippage * 10000}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                route_data = response.json()

                if not route_data["data"]:
                    logger.error(f"No route found for {input_mint} to {output_mint} (Attempt {attempt + 1}/{max_retries}).")
                    return None

                # Step 2: Generate Swap Transaction
                swap_transaction = route_data["data"][0]["swapTransaction"]
                transaction = Transaction.from_bytes(base64.b64decode(swap_transaction))

                # Step 3: Sign Transaction
                transaction.sign(wallet_keypair)

                # Step 4: Execute Transaction
                tx_signature = self.solana_client.send_raw_transaction(transaction.to_bytes())
                logger.info(f"Swap executed. Transaction signature: {tx_signature}")

                # Wait for confirmation (Optional but recommended)
                # You'd need to implement transaction confirmation logic here.

                return tx_signature

            except requests.exceptions.RequestException as e:
                logger.error(f"Error getting Jupiter quote (Attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(2 * (attempt + 1))  # Exponential backoff
            except Exception as e:
                logger.error(f"Error executing swap (Attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(2 * (attempt + 1))  # Exponential backoff

        logger.error(f"Failed to swap {input_mint} to {output_mint} after {max_retries} attempts.")
        return None