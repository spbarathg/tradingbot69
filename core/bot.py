import time
from ..data_acquisition.realtime_prices import PriceFetcher
from ..strategy.momentum_scalping import MomentumScalper
from ..strategy.risk_management import RiskManager
from ..execution.jup_swap import JupiterSwap
from ..ml_signals.surge_detection import SurgeDetector
from ..utils.logger import logger
from ..utils.config import config
from ..utils.helpers import is_valid_solana_address
import random

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

        # Reinforcement Learning Parameters
        self.q_table = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_decay_rate = 0.001

        # Initialize social scraper
        from ..data_acquisition.social_scraper import SocialScraper
        self.social_scraper = SocialScraper()

    def get_state(self, token_address):
        """
        Collects the current state information for a given token.
        This can include price data, social sentiment, volume, etc.
        """
        try:
            price_data = self.price_fetcher.get_price_dexscreener(token_address)
            if not price_data:
                logger.warning(f"Could not retrieve price data for {token_address}. Returning None.")
                return None

            # Example: Include price change, social sentiment, and volume in the state
            price_change = (price_data['price_usd'] - self.active_positions.get(token_address, price_data['price_usd'])) / self.active_positions.get(token_address, price_data['price_usd']) if token_address in self.active_positions else 0
            social_data = self.social_scraper.scrape_twitter(price_data['base_token_symbol'], num_tweets=50)
            sentiment_score = self.social_scraper.get_overall_sentiment([tweet for tweet in social_data]) if social_data else 0
            volume = price_data['volume_24h']

            # Collect all to state
            state = {
                'price_change': price_change,
                'sentiment_score': sentiment_score,
                'volume': volume
            }
            return state

        except Exception as e:
            logger.error(f"Error getting state for {token_address}: {e}")
            return None

    def choose_action(self, state):
        """
        Chooses an action based on the current state using a Q-table.
        """
        if not state:
            return 'hold'  # If no state, default to 'hold'

        # Convert state to a tuple to use as a key in the Q-table
        state_tuple = tuple(state.values())

        if state_tuple not in self.q_table:
            # Initialize Q-values for this state
            self.q_table[state_tuple] = {'buy': 0, 'sell': 0, 'hold': 0}

        # Exploration vs. Exploitation
        if random.uniform(0, 1) < self.epsilon:
            # Explore: choose a random action
            action = random.choice(['buy', 'sell', 'hold'])
        else:
            # Exploit: choose the action with the highest Q-value
            action = max(self.q_table[state_tuple], key=self.q_table[state_tuple].get)

        return action

    def update_q_value(self, state, action, reward, next_state):
        """
        Updates Q-value based on the reward received and the next state.
        """
        if not state or not next_state:
            return  # Ensure states are valid

        # Convert states to tuples
        state_tuple = tuple(state.values())
        next_state_tuple = tuple(next_state.values())

        # Ensure both states are in the Q-table
        if state_tuple not in self.q_table:
            self.q_table[state_tuple] = {'buy': 0, 'sell': 0, 'hold': 0}
        if next_state_tuple not in self.q_table:
            self.q_table[next_state_tuple] = {'buy': 0, 'sell': 0, 'hold': 0}

        # Q-learning update rule
        best_next_action = max(self.q_table[next_state_tuple], key=self.q_table[next_state_tuple].get)
        td_target = reward + self.discount_factor * self.q_table[next_state_tuple][best_next_action]
        td_error = td_target - self.q_table[state_tuple][action]

        # Update Q-value
        self.q_table[state_tuple][action] += self.learning_rate * td_error

    def reward_function(self, initial_price, final_price, action):
        """
        Defines the reward mechanism based on the outcome of the action.
        """
        profit = (final_price - initial_price) / initial_price

        if action == 'buy':
            return 1 if profit > 0 else -1  # Reward or penalize based on profit
        elif action == 'sell':
            return 1 if profit > 0 else -1
        else:
            return 0  # Neutral reward for holding

    def train(self, token_address, episodes=1000):
        """
        Trains the Q-table using Q-learning.
        """
        self.epsilon = 1.0  # Initial exploration rate

        for episode in range(episodes):
            state = self.get_state(token_address)
            if not state:
                logger.warning(f"Could not get initial state for {token_address}, skipping episode.")
                continue

            action = self.choose_action(state)
            initial_price = self.price_fetcher.get_price_dexscreener(token_address)['price_usd']

            # Simulate time passage for price changes
            time.sleep(1)
            final_price = self.price_fetcher.get_price_dexscreener(token_address)['price_usd']
            reward = self.reward_function(initial_price, final_price, action)

            next_state = self.get_state(token_address)
            if next_state:
                self.update_q_value(state, action, reward, next_state)

            # Decay epsilon
            self.epsilon = max(self.epsilon - self.epsilon_decay_rate, 0.01)  # Ensure it doesn't go below 0.01

            if episode % 100 == 0:
                logger.info(f"Episode {episode}, Epsilon: {self.epsilon}")

    def trade_loop(self, token_addresses: list):
        """
        Main trading loop that continuously checks for buy and sell signals.
        """
        if self.is_valid_solana_address:
            logger.info("Starting trading loop...")

            # Train the RL model first
            for token_address in token_addresses:
                self.train(token_address, episodes=1000)

            while True:
                try:
                    for token_address in token_addresses:
                        if not is_valid_solana_address(token_address):
                            logger.warning(f"Invalid token address: {token_address}. Skipping.")
                            continue

                        if token_address not in self.active_positions:
                            state = self.get_state(token_address)
                            action = self.choose_action(state)
                            if action == 'buy':
                                sol_to_buy = self.risk_manager.calculate_position_size()
                                if sol_to_buy > 0:
                                    try:
                                        tx_signature = self.jupiter_swap.swap(
                                            "So1111111111111111111111111111111111111112", token_address, sol_to_buy)
                                        if tx_signature:
                                            price_data = self.price_fetcher.get_price_dexscreener(token_address)
                                            self.active_positions[token_address] = price_data['price_usd']
                                            logger.info(f"Bought {token_address} at {price_data['price_usd']}. Active Positions {self.active_positions}")
                                        else:
                                            logger.warning(f"Failed to buy {token_address}.")
                                    except Exception as e:
                                        logger.error(f"Error during buy execution for {token_address}: {e}")
                        else:
                            state = self.get_state(token_address)
                            action = self.choose_action(state)
                            entry_price = self.active_positions[token_address]
                            price_data = self.price_fetcher.get_price_dexscreener(token_address)
                            if price_data:
                                current_price = price_data["price_usd"]
                                stop_loss_price = self.risk_manager.calculate_stop_loss_price(entry_price)
                                stop_loss_triggered = self.risk_manager.check_stop_loss(current_price, stop_loss_price)

                                if stop_loss_triggered:
                                    try:
                                        tx_signature = self.jupiter_swap.swap(
                                            token_address, "So1111111111111111111111111111111111111112", sol_to_buy)
                                        if tx_signature:
                                            del self.active_positions[token_address]
                                            logger.info(f"Sold {token_address} due to stop-loss. Active Positions {self.active_positions}")
                                        else:
                                            logger.warning(f"Failed to sell {token_address} due to stop-loss.")
                                    except Exception as e:
                                        logger.error(f"Error during sell execution (stop-loss) for {token_address}: {e}")
                                elif action == 'sell' and not stop_loss_triggered:
                                    try:
                                        tx_signature = self.jupiter_swap.swap(
                                            token_address, "So1111111111111111111111111111111111111112", sol_to_buy)
                                        if tx_signature:
                                            del self.active_positions[token_address]
                                            logger.info(f"Sold {token_address} at {current_price}. Active Positions {self.active_positions}")
                                        else:
                                            logger.warning(f"Failed to sell {token_address}.")
                                    except Exception as e:
                                        logger.error(f"Error during sell execution for {token_address}: {e}")

                    time.sleep(self.config.SLEEP_INTERVAL)

                except Exception as e:
                    logger.error(f"Error in the trading loop: {e}")

        else:
            logger.error("Invalid Solana wallet address.")