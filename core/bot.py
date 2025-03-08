import time
from ..data_acquisition.realtime_prices import PriceFetcher
from ..strategy.momentum_scalping import MomentumScalper
from ..strategy.risk_management import RiskManager
from ..execution.jup_swap import JupiterSwap
from ..ml_signals.surge_detection import SurgeDetector
from ..utils.logger import logger
from ..utils.config import config
from ..utils.helpers import is_valid_solana_address

class TradingBot:
    def __init__(self):
        self.price_fetcher = PriceFetcher()
        self.momentum_scalper = MomentumScalper()
        self.risk_manager = RiskManager()
        self.jupiter_swap = JupiterSwap()
        self.surge_detector = SurgeDetector()
        self.config = config
        self.wallet_address = ""
        try:
            from solders.keypair import Keypair
            wallet_keypair = Keypair.from_base58_string(self.config.WALLET_PRIVATE_KEY)
            self.wallet_address = str(wallet_keypair.pubkey())
        except Exception as e:
            logger.error(f"Private key is invalid or missing: {e}")
        self.active_positions = {}  # Dictionary to track active positions (token_address: entry_price)
        self.is_valid_solana_address = is_valid_solana_address(self.wallet_address)
        if not self.is_valid_solana_address:
            logger.error("Wallet Address is invalid. Please ensure the private key is the right one.")

    def trade_loop(self, token_addresses: list):
        """
        Main trading loop that continuously checks for buy and sell signals.
        """
        if self.is_valid_solana_address:
            logger.info("Starting trading loop...")
            while True:
                try:
                    for token_address in token_addresses:
                        if not is_valid_solana_address(token_address):
                            logger.warning(f"Invalid token address: {token_address}. Skipping.")
                            continue
                        if token_address not in self.active_positions:
                            #Check for Buy Signal
                            buy_signal = self.momentum_scalper.check_buy_signal(token_address)

                            if buy_signal:
                                # Calculate Position Size
                                sol_to_buy = self.risk_manager.calculate_position_size()
                                if sol_to_buy > 0:
                                    #Execute Buy Order
                                    try:
                                        # Assuming token_address is the output mint (what we want to buy) and SOL is the input
                                        tx_signature = self.jupiter_swap.swap("So1111111111111111111111111111111111111112", token_address, sol_to_buy)

                                        if tx_signature:
                                            #Record entry price
                                            price_data = self.price_fetcher.get_price_dexscreener(token_address)
                                            if price_data:
                                                self.active_positions[token_address] = price_data["price_usd"]
                                                logger.info(f"Bought {token_address} at {price_data['price_usd']}. Active Positions {self.active_positions}")
                                            else:
                                                logger.warning(f"Could not get entry price for {token_address} after buying.")
                                        else:
                                            logger.warning(f"Failed to buy {token_address}.")
                                    except Exception as e:
                                        logger.error(f"Error during buy execution for {token_address}: {e}")

                        else:
                            #Check for Sell Signal or Stop-Loss
                            entry_price = self.active_positions[token_address]
                            price_data = self.price_fetcher.get_price_dexscreener(token_address)

                            if price_data:
                                current_price = price_data["price_usd"]
                                #Check Stop Loss first
                                stop_loss_price = self.risk_manager.calculate_stop_loss_price(entry_price)
                                stop_loss_triggered = self.risk_manager.check_stop_loss(current_price, stop_loss_price)

                                if stop_loss_triggered:
                                    #Execute Sell Order (Stop-Loss)
                                    try:
                                        # Assuming token_address is the input mint (what we want to sell) and SOL is the output
                                        tx_signature = self.jupiter_swap.swap(token_address, "So1111111111111111111111111111111111111112", sol_to_buy) #Sell entire position
                                        if tx_signature:
                                            del self.active_positions[token_address]
                                            logger.info(f"Sold {token_address} due to stop-loss. Active Positions {self.active_positions}")
                                        else:
                                            logger.warning(f"Failed to sell {token_address} due to stop-loss.")
                                    except Exception as e:
                                        logger.error(f"Error during sell execution (stop-loss) for {token_address}: {e}")

                                else:
                                    #Check for Surge Potential
                                    surge_potential = self.surge_detector.detect_surge_potential(token_address)
                                    #Check Sell Signal (Profit Target)
                                    sell_signal = self.momentum_scalper.check_sell_signal(entry_price, current_price, surge_potential)

                                    if sell_signal:
                                        #Execute Sell Order (Profit Target)
                                        try:
                                            # Assuming token_address is the input mint (what we want to sell) and SOL is the output
                                            tx_signature = self.jupiter_swap.swap(token_address, "So1111111111111111111111111111111111111112", sol_to_buy)  # Sell entire position

                                            if tx_signature:
                                                del self.active_positions[token_address]
                                                logger.info(f"Sold {token_address} due to profit target. Active Positions: {self.active_positions}")
                                            else:
                                                logger.warning(f"Failed to sell {token_address} due to profit target.")
                                        except Exception as e:
                                            logger.error(f"Error during sell execution (profit target) for {token_address}: {e}")
                            else:
                                logger.warning(f"Could not retrieve price data for {token_address}. Skipping sell check.")
                    time.sleep(10)  # Check every 10 seconds (adjust as needed)

                except Exception as e:
                    logger.error(f"Error in main trading loop: {e}")
                    time.sleep(60)  # Wait longer after an error
        else:
            logger.error("Trading cannot begin")

# Example Usage (in main.py or a test script)
if __name__ == '__main__':
    bot = TradingBot()
    token_addresses = ["EjmcZ9EcE6JMRyASG4sJ49tfzdR16gJ1eQGm2UjGVkJ"]  # Replace with real token addresses
    bot.trade_loop(token_addresses)