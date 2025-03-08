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
class JupiterSwap:
    def __init__(self):
        self.private_key = config.WALLET_PRIVATE_KEY
        self.solana_client = Client("https://api.mainnet-beta.solana.com") # Consider your RPC endpoint
        self.slippage = config.SLIPPAGE_TOLERANCE
        self.jupiter_api_url = config.JUPITER_API_URL  # From config

    def swap(self, input_mint: str, output_mint: str, amount: float) -> str:
        """
        Executes a swap using the Jupiter aggregator.

        Args:
            input_mint (str): The mint address of the input token.
            output_mint (str): The mint address of the output token.
            amount (float): The amount of the input token to swap (in SOL).

        Returns:
            str: The transaction signature if the swap was successful, None otherwise.
        """
        try:
            wallet_keypair = Keypair.from_base58_string(self.private_key)
            wallet_address = str(wallet_keypair.pubkey())
            #Ensure wallet has enough balance to complete the swap
            has_enough_balance = check_enough_sol_balance(wallet_address, amount)
            if not has_enough_balance:
                return None
            # Step 1: Get Route
            url = f"{self.jupiter_api_url}/quote?inputMint={input_mint}&outputMint={output_mint}&amount={amount * 10**9}&slippageBps={self.slippage * 10000}"
            response = requests.get(url)
            response.raise_for_status() # Raise HTTPError for bad responses
            route_data = response.json()

            if not route_data["data"]:
                logger.error("No route found for the given input and output tokens.")
                return None

            # Step 2: Generate Swap Transaction
            swap_transaction = route_data["data"][0]["swapTransaction"]
            # Decompile transaction from base64
            transaction = Transaction.from_bytes(base64.b64decode(swap_transaction))

            # Step 3: Sign Transaction
            transaction.sign(wallet_keypair)

            # Step 4: Execute Transaction
            tx_signature = self.solana_client.send_raw_transaction(transaction.to_bytes())
            logger.info(f"Swap executed. Transaction signature: {tx_signature}")

            return tx_signature

        except Exception as e:
            logger.error(f"Error executing swap: {e}")
            return None

# Example Usage (Remember to replace with actual mint addresses and amount)
if __name__ == '__main__':
    #Test only with Mainnet Tokens
    jupiter_swap = JupiterSwap()
    input_mint = "So1111111111111111111111111111111111111112"  # SOL Mint Address
    output_mint = "EPjFWdd5AufqALUs2vW0ouAZnuuzqvTZcztBbuw61zPX" #USDC Mint Address
    amount = 0.01 #Amount to swap
    tx_signature = jupiter_swap.swap(input_mint, output_mint, amount)
    if tx_signature:
        print(f"Swap successful. Transaction signature: {tx_signature}")
    else:
        print("Swap failed.")