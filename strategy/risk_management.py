from ..utils.logger import logger
from ..utils.config import config
from ..utils.helpers import get_solana_price_usd

class RiskManager:
    def __init__(self):
        self.stop_loss_percentage = config.STOP_LOSS_PERCENTAGE
        self.initial_investment_usd = config.INITIAL_INVESTMENT_USD

    def calculate_position_size(self, risk_percentage: float = 0.02) -> float:
        """
        Calculates the position size based on risk percentage and SOL price.

        Args:
            risk_percentage (float): The percentage of the initial investment to risk on a single trade.

        Returns:
            float: The amount of SOL to buy for the position.
        """
        try:
            sol_price = get_solana_price_usd()
            if not sol_price:
                logger.error("Could not fetch SOL price. Using a default SOL price of $20.")
                sol_price = 20  # Default price

            # Amount to risk on trade
            risk_amount_usd = self.initial_investment_usd * risk_percentage
            # Amount of SOL to buy
            sol_to_buy = risk_amount_usd / sol_price
            logger.info(f"Calculated position size: Risking ${risk_amount_usd:.2f} to buy {sol_to_buy:.4f} SOL (SOL price: ${sol_price:.2f})")
            return sol_to_buy

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0

    def calculate_stop_loss_price(self, entry_price: float) -> float:
        """
        Calculates the stop-loss price based on the entry price and stop-loss percentage.

        Args:
            entry_price (float): The price at which the token was bought.

        Returns:
            float: The stop-loss price.
        """
        stop_loss_price = entry_price * (1 - self.stop_loss_percentage)
        logger.info(f"Calculated stop-loss price: {stop_loss_price:.6f} (Entry price: {entry_price:.6f}, Stop-loss percentage: {self.stop_loss_percentage})")
        return stop_loss_price

    def check_stop_loss(self, current_price: float, stop_loss_price: float) -> bool:
        """
        Checks if the stop-loss has been triggered.

        Args:
            current_price (float): The current price of the token.
            stop_loss_price (float): The stop-loss price.

        Returns:
            bool: True if the stop-loss has been triggered, False otherwise.
        """
        if current_price <= stop_loss_price:
            logger.info("Stop-loss triggered!")
            return True
        else:
            return False

# Example Usage
if __name__ == '__main__':
    risk_manager = RiskManager()
    
    # Calculate position size based on risk percentage
    position_size = risk_manager.calculate_position_size(risk_percentage=0.02)
    print(f"Position size: {position_size} SOL")

    entry_price = 0.001234  # Example entry price
    stop_loss_price = risk_manager.calculate_stop_loss_price(entry_price)
    print(f"Stop-loss price: {stop_loss_price}")

    current_price = 0.0011  # Example current price
    stop_loss_triggered = risk_manager.check_stop_loss(current_price, stop_loss_price)
    print(f"Stop-loss triggered: {stop_loss_triggered}")