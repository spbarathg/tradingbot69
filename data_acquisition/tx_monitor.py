import asyncio
import logging
from typing import Dict, Optional
from solders.rpc.api import Client
from solders.rpc.config import RpcContextConfig
from solders.signature import Signature
from solders.transaction_status import TransactionConfirmationStatus

from ..utils.logger import logger
from ..utils.config import config


class TxMonitor:
    def __init__(self):
        """Initialize the transaction monitor with a Solana RPC client."""
        self.rpc_client = Client(config.SOLANA_RPC_URL)
        self.max_retries = 5  # Maximum number of retries for transaction confirmation
        self.retry_delay = 2  # Initial delay between retries in seconds
        self.rate_limit_interval = timedelta(seconds=1)  # Rate limit: 1 call per second
        self.last_api_call_time = datetime.now()

    async def confirm_transaction(self, tx_signature: str) -> bool:
        """
        Confirm that a transaction is finalized on the Solana blockchain.
        
        Args:
            tx_signature: The transaction signature (hash) to monitor.
        
        Returns:
            bool: True if the transaction is confirmed, False otherwise.
        """
        signature = Signature.from_string(tx_signature)
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                await self._enforce_rate_limit()

                # Fetch the transaction status
                tx_status = await self.rpc_client.get_signature_status(signature, RpcContextConfig(commitment="confirmed"))
                if tx_status is None:
                    logger.warning(f"Transaction {tx_signature} not found (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                    continue

                # Check if the transaction is confirmed
                if tx_status.confirmation_status == TransactionConfirmationStatus.Finalized:
                    logger.info(f"Transaction {tx_signature} confirmed.")
                    return True
                else:
                    logger.warning(f"Transaction {tx_signature} not yet finalized (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
            except Exception as e:
                logger.error(f"Error confirming transaction {tx_signature}: {e}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff

        logger.error(f"Failed to confirm transaction {tx_signature} after {self.max_retries} attempts.")
        return False

    async def monitor_transactions(self, tx_signatures: Dict[str, str]) -> Dict[str, bool]:
        """
        Monitor a batch of transactions and return their confirmation status.
        
        Args:
            tx_signatures: A dictionary of transaction signatures and their associated token addresses.
        
        Returns:
            Dict[str, bool]: A dictionary mapping token addresses to their transaction confirmation status.
        """
        results = {}
        for token_address, tx_signature in tx_signatures.items():
            confirmed = await self.confirm_transaction(tx_signature)
            results[token_address] = confirmed
            if not confirmed:
                await self.handle_failed_transaction(tx_signature, token_address)
        return results

    async def handle_failed_transaction(self, tx_signature: str, token_address: str) -> None:
        """
        Handle a failed transaction by retrying or triggering a fallback mechanism.
        
        Args:
            tx_signature: The transaction signature (hash) that failed.
            token_address: The token address associated with the transaction.
        """
        logger.warning(f"Handling failed transaction {tx_signature} for token {token_address}.")
        # Implement retry logic or fallback mechanism here
        # Example: Retry the transaction with higher gas fees
        # Example: Notify the trading bot to adjust its strategy

    async def send_alert(self, message: str) -> None:
        """
        Send an alert (e.g., via email, Slack, or Telegram) for critical events.
        
        Args:
            message: The alert message to send.
        """
        # Example: Integrate with a notification service (e.g., Slack, Telegram)
        logger.info(f"ALERT: {message}")

    async def _enforce_rate_limit(self) -> None:
        """
        Ensures API calls respect the rate limit.
        """
        time_since_last_call = datetime.now() - self.last_api_call_time
        if time_since_last_call < self.rate_limit_interval:
            await asyncio.sleep((self.rate_limit_interval - time_since_last_call).total_seconds())
        self.last_api_call_time = datetime.now()