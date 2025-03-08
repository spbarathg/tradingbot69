import time
import random
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from functools import lru_cache
from datetime import datetime, timedelta

from ..data_acquisition.realtime_prices import PriceFetcher
from ..strategy.momentum_scalping import MomentumScalper
from ..strategy.risk_management import RiskManager
from ..execution.jup_swap import JupiterSwap
from ..ml_signals.surge_detection import SurgeDetector
from ..data_acquisition.social_scraper import SocialScraper
from ..utils.logger import logger
from ..utils.config import config
from ..utils.helpers import is_valid_solana_address, async_retry_with_backoff


@dataclass
class State:
    """Represents the state of a token for reinforcement learning."""
    price_change: float
    sentiment_score: float
    volume: float
    volatility: float  # Added volatility for dynamic position sizing

    def to_tuple(self) -> Tuple[float, float, float, float]:
        """Convert state to tuple for use as dictionary key."""
        return (self.price_change, self.sentiment_score, self.volume, self.volatility)


class TradingBot:
    """AI-powered trading bot integrating reinforcement learning, sentiment analysis, 
    and surge detection to optimize token trading decisions."""

    # Constants and configuration parameters
    SOL_ADDRESS = "So1111111111111111111111111111111111111112"
    ACTIONS = ['buy', 'sell', 'hold']
    MIN_EPSILON = 0.01
    MAX_Q_TABLE_SIZE = 10000  # Prevent memory bloat in Q-table
    CACHE_TTL = 60  # Price data cache time-to-live in seconds
    API_CALL_INTERVAL = 1  # Rate limit: 1 API call per second
    PARTIAL_SELL_PERCENTAGE = 0.25  # Percentage to sell gradually during a surge
    DYNAMIC_POSITION_SCALING = True  # Enable dynamic position sizing based on volatility

    def __init__(self):
        """Initialize the trading bot and all integrated components."""
        self.price_fetcher = PriceFetcher()
        self.momentum_scalper = MomentumScalper()
        self.risk_manager = RiskManager()
        self.jupiter_swap = JupiterSwap()
        self.surge_detector = SurgeDetector()  # For detecting potential explosive growth
        self.social_scraper = SocialScraper()
        self.config = config

        # Wallet and positions setup
        self.wallet_address = self._initialize_wallet()
        self.active_positions: Dict[str, float] = {}  # token_address -> entry_price
        self.hold_mode: Dict[str, bool] = {}  # token_address -> surge hold flag

        # Reinforcement Learning setup
        self.q_table: Dict[Tuple, Dict[str, float]] = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_decay_rate = 0.001

        # Rate limiting and caching for price data
        self.last_api_call_time = datetime.now()
        self.price_cache: Dict[str, Tuple[Dict, datetime]] = {}  # token_address -> (price_data, timestamp)

    def _initialize_wallet(self) -> str:
        """Initialize and validate wallet from private key."""
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

    @async_retry_with_backoff(retries=3, backoff_in_seconds=2)
    async def _fetch_price_data_batch(self, token_addresses: List[str]) -> Dict[str, Dict]:
        """Fetch price data for multiple tokens using batch requests."""
        # Rate limiting
        time_since_last_call = datetime.now() - self.last_api_call_time
        if time_since_last_call < timedelta(seconds=self.API_CALL_INTERVAL):
            await asyncio.sleep((timedelta(seconds=self.API_CALL_INTERVAL) - time_since_last_call).total_seconds())
        self.last_api_call_time = datetime.now()

        try:
            price_data = await self.price_fetcher.get_prices_dexscreener_batch(token_addresses)
            return price_data
        except Exception as e:
            logger.error(f"Error fetching batch price data: {e}")
            return {}

    @lru_cache(maxsize=128)
    async def _fetch_price_data(self, token_address: str) -> Optional[Dict]:
        """Fetch and cache price data for a single token."""
        if token_address in self.price_cache:
            price_data, timestamp = self.price_cache[token_address]
            if datetime.now() - timestamp < timedelta(seconds=self.CACHE_TTL):
                return price_data

        price_data = await self._fetch_price_data_batch([token_address])
        if token_address in price_data:
            self.price_cache[token_address] = (price_data[token_address], datetime.now())
            return price_data[token_address]
        return None

    async def get_state(self, token_address: str) -> Optional[State]:
        """Collect current market state information for a given token."""
        price_data = await self._fetch_price_data(token_address)
        if not price_data:
            return None

        current_price = price_data['price_usd']
        entry_price = self.active_positions.get(token_address, current_price)
        price_change = ((current_price - entry_price) / entry_price) if token_address in self.active_positions else 0

        token_symbol = price_data['base_token_symbol']
        social_data = await self.social_scraper.scrape_twitter(token_symbol, num_tweets=50)
        sentiment_score = self.social_scraper.get_overall_sentiment(social_data) if social_data else 0

        # Calculate volatility (standard deviation of price changes over a short period)
        volatility = await self.price_fetcher.calculate_volatility(token_address)

        return State(
            price_change=price_change,
            sentiment_score=sentiment_score,
            volume=price_data['volume_24h'],
            volatility=volatility
        )

    def choose_action(self, state: Optional[State]) -> str:
        """Select an action (buy, sell, or hold) based on the current state using Q-learning."""
        if not state:
            return 'hold'

        state_tuple = state.to_tuple()
        if state_tuple not in self.q_table:
            self.q_table[state_tuple] = {action: 0 for action in self.ACTIONS}

        # Exploration vs. Exploitation decision
        if random.uniform(0, 1) < self.epsilon:
            return random.choice(self.ACTIONS)
        return max(self.q_table[state_tuple], key=self.q_table[state_tuple].get)

    def update_q_value(self, state: State, action: str, reward: float, next_state: State) -> None:
        """Update Q-table values based on observed rewards and the transition to the next state."""
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

        # Maintain Q-table size
        if len(self.q_table) > self.MAX_Q_TABLE_SIZE:
            oldest_state = next(iter(self.q_table))
            del self.q_table[oldest_state]

    def reward_function(self, initial_price: float, final_price: float, action: str) -> float:
        """Define reward based on profit percentage and the action taken."""
        profit_percentage = (final_price - initial_price) / initial_price * 100
        if action == 'buy':
            return profit_percentage / 10
        elif action == 'sell':
            return -profit_percentage / 10
        return profit_percentage / 20

    async def train(self, token_address: str, episodes: int = 1000) -> None:
        """Train the Q-learning model on a specific token over a number of episodes."""
        logger.info(f"Starting training on {token_address} for {episodes} episodes")
        self.epsilon = 1.0

        for episode in range(episodes):
            state = await self.get_state(token_address)
            if not state:
                logger.warning(f"Could not retrieve initial state for {token_address}. Skipping episode.")
                continue

            action = self.choose_action(state)
            price_data = await self._fetch_price_data(token_address)
            if not price_data:
                continue

            initial_price = price_data['price_usd']
            await asyncio.sleep(1)  # Simulate time passage between states
            final_price = (await self._fetch_price_data(token_address))['price_usd']
            reward = self.reward_function(initial_price, final_price, action)
            next_state = await self.get_state(token_address)
            if next_state:
                self.update_q_value(state, action, reward, next_state)

            # Decay exploration rate gradually
            self.epsilon = max(self.epsilon - self.epsilon_decay_rate, self.MIN_EPSILON)
            if episode % 100 == 0:
                logger.info(f"Episode {episode}/{episodes}, epsilon: {self.epsilon:.4f}")

        logger.info(f"Training completed on {token_address}. Final epsilon: {self.epsilon:.4f}")

    @async_retry_with_backoff(retries=3, backoff_in_seconds=2)
    async def execute_buy(self, token_address: str, state: Optional[State] = None) -> bool:
        """Execute a buy order for the specified token."""
        if self.DYNAMIC_POSITION_SCALING and state:
            # Adjust position size dynamically based on volatility
            volatility = state.volatility
            base_position_size = self.risk_manager.calculate_position_size()
            adjusted_position_size = base_position_size * (1 - volatility)  # Reduce size in high volatility
            sol_to_buy = max(adjusted_position_size, 0)  # Ensure non-negative
            logger.debug(f"Dynamic position sizing: volatility={volatility:.4f}, adjusted_size={sol_to_buy:.4f}")
        else:
            sol_to_buy = self.risk_manager.calculate_position_size()

        if sol_to_buy <= 0:
            logger.warning(f"Calculated position size is {sol_to_buy}. Skipping buy for {token_address}.")
            return False

        try:
            tx_signature = await self.jupiter_swap.swap(self.SOL_ADDRESS, token_address, sol_to_buy)
            if not tx_signature:
                logger.warning(f"Buy order failed for {token_address}.")
                return False

            price_data = await self._fetch_price_data(token_address)
            if not price_data:
                logger.warning(f"Buy executed for {token_address} but failed to retrieve price data.")
                return False

            self.active_positions[token_address] = price_data['price_usd']
            # Reset hold mode flag on new position
            self.hold_mode[token_address] = False
            logger.info(f"Bought {token_address} at {price_data['price_usd']}.")
            return True
        except Exception as e:
            logger.error(f"Error during buy execution for {token_address}: {e}")
            return False

    @async_retry_with_backoff(retries=3, backoff_in_seconds=2)
    async def execute_sell(self, token_address: str, partial: bool = False, reason: str = "strategy") -> bool:
        """Execute a sell order (either full or partial) for the specified token."""
        try:
            # Determine the amount to sell: full position or a percentage during a surge hold
            if partial:
                sell_percentage = self.PARTIAL_SELL_PERCENTAGE
            else:
                sell_percentage = 1.0
            sol_amount = self.risk_manager.calculate_position_size() * sell_percentage

            tx_signature = await self.jupiter_swap.swap(token_address, self.SOL_ADDRESS, sol_amount)
            if not tx_signature:
                logger.warning(f"Sell order failed for {token_address}.")
                return False

            price_data = await self._fetch_price_data(token_address)
            current_price = price_data['price_usd'] if price_data else "unknown"
            logger.info(f"Sold {sell_percentage*100:.0f}% of {token_address} at {current_price} due to {reason}.")

            # For full sell, remove the token from active positions; for partial, adjust the entry price
            if not partial:
                self.active_positions.pop(token_address, None)
                self.hold_mode[token_address] = False
            return True
        except Exception as e:
            logger.error(f"Error during sell execution for {token_address}: {e}")
            return False

    async def process_token(self, token_address: str) -> None:
        """Evaluate a token and decide whether to buy, sell, or hold based on current state and surge detection."""
        if not is_valid_solana_address(token_address):
            logger.warning(f"Invalid token address: {token_address}. Skipping.")
            return

        state = await self.get_state(token_address)
        if not state:
            logger.warning(f"Could not retrieve state for {token_address}.")
            return

        # Check surge potential using the integrated SurgeDetector
        surge_signal = await self.surge_detector.detect_surges(token_address)
        if surge_signal:
            # If surge is detected, switch to hold mode if not already set
            if not self.hold_mode.get(token_address, False):
                logger.info(f"Surge signal detected for {token_address}. Switching to hold mode for gradual exit.")
                self.hold_mode[token_address] = True

        # If we don't hold and no active position exists, consider buying
        if token_address not in self.active_positions and not self.hold_mode.get(token_address, False):
            action = self.choose_action(state)
            if action == 'buy':
                await self.execute_buy(token_address, state)
            return

        # For tokens in active positions, check risk (e.g., stop-loss) and decide on selling strategy
        price_data = await self._fetch_price_data(token_address)
        if not price_data:
            logger.warning(f"Missing price data for {token_address}.")
            return

        current_price = price_data["price_usd"]
        entry_price = self.active_positions.get(token_address, current_price)
        stop_loss_price = self.risk_manager.calculate_dynamic_stop_loss(entry_price, current_price)

        # If stop-loss conditions are met, perform a full sell
        if self.risk_manager.check_stop_loss(current_price, stop_loss_price):
            await self.execute_sell(token_address, partial=False, reason="stop-loss")
            return

        # If the bot is in surge hold mode, execute a partial sell strategy to gradually lock in profits
        if self.hold_mode.get(token_address, False):
            await self.execute_sell(token_address, partial=True, reason="surge hold partial exit")
        else:
            # Otherwise, follow the standard strategy: if action suggests selling, exit fully.
            action = self.choose_action(state)
            if action == 'sell':
                await self.execute_sell(token_address, partial=False, reason="strategy")

    async def trade_loop(self, token_addresses: List[str]) -> None:
        """Main trading loop that continuously evaluates tokens and applies trading strategies."""
        if not self.wallet_address:
            logger.error("Invalid or missing wallet address. Trading loop cannot start.")
            return

        logger.info(f"Starting trading loop for {len(token_addresses)} tokens...")

        # Initial training phase for each token
        for token_address in token_addresses:
            if is_valid_solana_address(token_address):
                await self.train(token_address, episodes=1000)
            else:
                logger.warning(f"Skipping training for invalid token address: {token_address}")

        # Main loop for live trading decisions
        try:
            while True:
                tasks = [self.process_token(token_address) for token_address in token_addresses]
                await asyncio.gather(*tasks)
                await asyncio.sleep(self.config.SLEEP_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Trading loop stopped by user.")
        except Exception as e:
            logger.error(f"Critical error in trading loop: {e}")