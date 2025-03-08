import time
import random
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..data_acquisition.realtime_prices import PriceFetcher
from ..strategy.momentum_scalping import MomentumScalper
from ..strategy.risk_management import RiskManager
from ..execution.jup_swap import JupiterSwap
from ..ml_signals.surge_detection import SurgeDetector
from ..data_acquisition.social_scraper import SocialScraper
from ..utils.logger import logger
from ..utils.config import config
from ..utils.helpers import is_valid_solana_address


@dataclass
class State:
    """Represents the state of a token for reinforcement learning."""
    price_change: float
    sentiment_score: float
    volume: float

    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert state to tuple for use as dictionary key."""
        return (self.price_change, self.sentiment_score, self.volume)


class TradingBot:
    """Trading bot that uses reinforcement learning to make trading decisions."""
    
    # Constants
    SOL_ADDRESS = "So1111111111111111111111111111111111111112"
    ACTIONS = ['buy', 'sell', 'hold']
    MIN_EPSILON = 0.01
    
    def __init__(self):
        """Initialize the trading bot and its components."""
        self.price_fetcher = PriceFetcher()
        self.momentum_scalper = MomentumScalper()
        self.risk_manager = RiskManager()
        self.jupiter_swap = JupiterSwap()
        self.surge_detector = SurgeDetector()
        self.social_scraper = SocialScraper()
        self.config = config
        
        # Wallet setup
        self.wallet_address = self._initialize_wallet()
        self.active_positions: Dict[str, float] = {}  # token_address -> entry_price
        
        # Reinforcement Learning setup
        self.q_table: Dict[Tuple, Dict[str, float]] = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_decay_rate = 0.001

    def _initialize_wallet(self) -> str:
        """Initialize wallet from private key and validate it."""
        try:
            from solders.keypair import Keypair
            wallet_keypair = Keypair.from_base58_string(self.config.WALLET_PRIVATE_KEY)
            wallet_address = str(wallet_keypair.pubkey())
            
            if not is_valid_solana_address(wallet_address):
                logger.error("Wallet address is invalid. Please check your private key.")
                return ""
            return wallet_address
        except ImportError:
            logger.error("Failed to import solders.keypair. Make sure it's installed.")
        except Exception as e:
            logger.error(f"Private key is invalid or missing: {e}")
        return ""

    def _fetch_price_data(self, token_address: str) -> Optional[Dict]:
        """Fetch price data for a token."""
        try:
            price_data = self.price_fetcher.get_price_dexscreener(token_address)
            if not price_data:
                logger.warning(f"No price data for {token_address}")
            return price_data
        except Exception as e:
            logger.error(f"Error fetching price data for {token_address}: {e}")
            return None

    def get_state(self, token_address: str) -> Optional[State]:
        """Collect current state information for a given token."""
        price_data = self._fetch_price_data(token_address)
        if not price_data:
            return None

        # Calculate price change
        current_price = price_data['price_usd']
        entry_price = self.active_positions.get(token_address, current_price)
        price_change = (current_price - entry_price) / entry_price if token_address in self.active_positions else 0
        
        # Get social sentiment data
        token_symbol = price_data['base_token_symbol']
        social_data = self.social_scraper.scrape_twitter(token_symbol, num_tweets=50)
        sentiment_score = self.social_scraper.get_overall_sentiment(social_data) if social_data else 0
        
        return State(
            price_change=price_change,
            sentiment_score=sentiment_score,
            volume=price_data['volume_24h']
        )

    def choose_action(self, state: Optional[State]) -> str:
        """Choose an action based on the current state using the Q-table."""
        if not state:
            return 'hold'

        state_tuple = state.to_tuple()
        if state_tuple not in self.q_table:
            self.q_table[state_tuple] = {action: 0 for action in self.ACTIONS}

        # Exploration vs. Exploitation
        if random.uniform(0, 1) < self.epsilon:
            return random.choice(self.ACTIONS)
        return max(self.q_table[state_tuple], key=self.q_table[state_tuple].get)

    def update_q_value(self, state: State, action: str, reward: float, next_state: State) -> None:
        """Update Q-value based on the reward received and the next state."""
        if not state or not next_state:
            return

        state_tuple = state.to_tuple()
        next_state_tuple = next_state.to_tuple()

        if state_tuple not in self.q_table:
            self.q_table[state_tuple] = {action: 0 for action in self.ACTIONS}
        if next_state_tuple not in self.q_table:
            self.q_table[next_state_tuple] = {action: 0 for action in self.ACTIONS}

        best_next_action = max(self.q_table[next_state_tuple], key=self.q_table[next_state_tuple].get)
        td_target = reward + self.discount_factor * self.q_table[next_state_tuple][best_next_action]
        td_error = td_target - self.q_table[state_tuple][action]
        self.q_table[state_tuple][action] += self.learning_rate * td_error

    def reward_function(self, initial_price: float, final_price: float, action: str) -> float:
        """Define the reward mechanism based on the outcome of the action."""
        profit_percentage = (final_price - initial_price) / initial_price * 100
        if action == 'buy':
            return profit_percentage / 10
        elif action == 'sell':
            return -profit_percentage / 10
        return profit_percentage / 20

    def train(self, token_address: str, episodes: int = 1000) -> None:
        """Train the Q-table using Q-learning."""
        logger.info(f"Starting training on {token_address} for {episodes} episodes")
        self.epsilon = 1.0

        for episode in range(episodes):
            state = self.get_state(token_address)
            if not state:
                logger.warning(f"Could not get initial state for {token_address}, skipping episode.")
                continue

            action = self.choose_action(state)
            price_data = self._fetch_price_data(token_address)
            if not price_data:
                continue

            initial_price = price_data['price_usd']
            time.sleep(1)  # Simulate time passage
            final_price = self._fetch_price_data(token_address)['price_usd']
            reward = self.reward_function(initial_price, final_price, action)

            next_state = self.get_state(token_address)
            if next_state:
                self.update_q_value(state, action, reward, next_state)

            self.epsilon = max(self.epsilon - self.epsilon_decay_rate, self.MIN_EPSILON)
            if episode % 100 == 0:
                logger.info(f"Training progress: Episode {episode}/{episodes}, Epsilon: {self.epsilon:.4f}")

        logger.info(f"Training completed on {token_address}. Final epsilon: {self.epsilon:.4f}")

    def execute_buy(self, token_address: str) -> bool:
        """Execute a buy order for the given token."""
        sol_to_buy = self.risk_manager.calculate_position_size()
        if sol_to_buy <= 0:
            logger.warning(f"Position size calculation returned {sol_to_buy}, skipping buy.")
            return False

        try:
            tx_signature = self.jupiter_swap.swap(self.SOL_ADDRESS, token_address, sol_to_buy)
            if not tx_signature:
                logger.warning(f"Failed to buy {token_address}.")
                return False

            price_data = self._fetch_price_data(token_address)
            if not price_data:
                logger.warning(f"Bought {token_address} but couldn't get price data.")
                return False

            self.active_positions[token_address] = price_data['price_usd']
            logger.info(f"Bought {token_address} at {price_data['price_usd']}. Active Positions: {self.active_positions}")
            return True
        except Exception as e:
            logger.error(f"Error during buy execution for {token_address}: {e}")
            return False

    def execute_sell(self, token_address: str, reason: str = "strategy") -> bool:
        """Execute a sell order for the given token."""
        try:
            sol_amount = self.risk_manager.calculate_position_size()
            tx_signature = self.jupiter_swap.swap(token_address, self.SOL_ADDRESS, sol_amount)
            if not tx_signature:
                logger.warning(f"Failed to sell {token_address}.")
                return False

            price_data = self._fetch_price_data(token_address)
            current_price = price_data['price_usd'] if price_data else "unknown"
            logger.info(f"Sold {token_address} at {current_price} due to {reason}. Previous positions: {self.active_positions}")

            if token_address in self.active_positions:
                del self.active_positions[token_address]
            return True
        except Exception as e:
            logger.error(f"Error during sell execution for {token_address}: {e}")
            return False

    def process_token(self, token_address: str) -> None:
        """Process a single token for trading decisions."""
        if not is_valid_solana_address(token_address):
            logger.warning(f"Invalid token address: {token_address}. Skipping.")
            return

        state = self.get_state(token_address)
        if not state:
            logger.warning(f"Could not get state for {token_address}, skipping.")
            return

        action = self.choose_action(state)
        if token_address not in self.active_positions:
            if action == 'buy':
                self.execute_buy(token_address)
            return

        price_data = self._fetch_price_data(token_address)
        if not price_data:
            logger.warning(f"Could not get price data for {token_address}, skipping.")
            return

        current_price = price_data["price_usd"]
        entry_price = self.active_positions[token_address]
        stop_loss_price = self.risk_manager.calculate_stop_loss_price(entry_price)
        if self.risk_manager.check_stop_loss(current_price, stop_loss_price):
            self.execute_sell(token_address, reason="stop-loss")
            return

        if action == 'sell':
            self.execute_sell(token_address, reason="strategy")

    def trade_loop(self, token_addresses: List[str]) -> None:
        """Main trading loop that continuously checks for buy and sell signals."""
        if not self.wallet_address:
            logger.error("Invalid or missing wallet address. Trading loop cannot start.")
            return

        logger.info(f"Starting trading loop for {len(token_addresses)} tokens...")
        for token_address in token_addresses:
            if is_valid_solana_address(token_address):
                self.train(token_address, episodes=1000)
            else:
                logger.warning(f"Skipping training for invalid token address: {token_address}")

        try:
            while True:
                for token_address in token_addresses:
                    try:
                        self.process_token(token_address)
                    except Exception as e:
                        logger.error(f"Error processing token {token_address}: {e}")
                        continue
                time.sleep(self.config.SLEEP_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Trading loop stopped by user.")
        except Exception as e:
            logger.error(f"Critical error in trading loop: {e}")