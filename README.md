# Solana Trading Bot

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

A **high-frequency trading bot** built for the Solana blockchain, designed to automate trading strategies using **real-time price data**, **social sentiment analysis**, and **reinforcement learning**. The bot integrates with **Jupiter DEX** for swaps and **Dexscreener** for price feeds, enabling efficient and profitable trading.

---

## Features

- **Real-Time Price Data**: Fetches real-time token prices from Dexscreener.
- **Social Sentiment Analysis**: Scrapes and analyzes social media (e.g., Twitter, Reddit) to detect market trends.
- **Reinforcement Learning**: Uses Q-learning to make trading decisions based on market conditions.
- **Dynamic Risk Management**: Implements stop-loss and position sizing based on volatility and risk tolerance.
- **Asynchronous Execution**: Built with `asyncio` for high-performance, non-blocking operations.
- **Customizable Strategies**: Easily configurable trading parameters (e.g., slippage, profit thresholds).
- **Graceful Shutdown**: Handles interruptions gracefully to ensure safe shutdowns.

---

## Prerequisites

Before running the bot, ensure you have the following:

- **Python 3.8+**: The bot is written in Python.
- **Solana Wallet**: A Solana wallet with a private key for executing trades.
- **Dexscreener API Key**: For fetching real-time price data (optional, but recommended).
- **Jupiter API Access**: For executing swaps on the Jupiter DEX aggregator.

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/solana-trading-bot.git
   cd solana-trading-bot
   ```

2. **Install Dependencies**:
   Install the required Python packages using `pip`:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**:
   Create a `.env` file in the root directory and add the following:
   ```plaintext
   WALLET_PRIVATE_KEY=your_wallet_private_key_here
   DEXSCREENER_API_KEY=your_dexscreener_api_key_here
   JUPITER_API_URL=https://quote-api.jup.ag/v6
   SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret
   REDDIT_USER_AGENT=your_reddit_user_agent
   ```

4. **Install Optional Dependencies**:
   If you need additional functionality (e.g., Solana FM monitoring), install the optional dependencies:
   ```bash
   pip install solana-fm-py
   ```

---

## Usage

### Running the Bot

To start the bot, run the following command:
```bash
python main.py
```

### Configuration

The bot can be configured using the following environment variables:

| Variable                | Description                                                                 | Default Value                     |
|-------------------------|-----------------------------------------------------------------------------|-----------------------------------|
| `WALLET_PRIVATE_KEY`    | Your Solana wallet private key.                                             | **Required**                      |
| `DEXSCREENER_API_KEY`   | Dexscreener API key for fetching price data.                                | Optional                          |
| `JUPITER_API_URL`       | Jupiter API endpoint for swaps.                                             | `https://quote-api.jup.ag/v6`     |
| `SOLANA_RPC_URL`        | Solana RPC endpoint for blockchain interactions.                            | `https://api.mainnet-beta.solana.com` |
| `TOKENS_TO_TRADE`       | Comma-separated list of token addresses to trade.                           | Default Solana and USDC addresses |
| `SLIPPAGE_TOLERANCE`    | Slippage tolerance for swaps (e.g., 0.005 for 0.5%).                        | `0.005`                           |
| `PROFIT_THRESHOLD`      | Profit threshold for selling (e.g., 0.45 for 45%).                         | `0.45`                            |
| `STOP_LOSS_PERCENTAGE`  | Stop-loss percentage (e.g., 0.10 for 10%).                                  | `0.10`                            |
| `INITIAL_INVESTMENT_USD`| Initial investment amount in USD.                                           | `100`                             |

---

## Bot Workflow

1. **Fetch Real-Time Data**:
   - The bot fetches real-time price data from Dexscreener and social sentiment data from Twitter/Reddit.

2. **Analyze Market Conditions**:
   - Uses reinforcement learning (Q-learning) to analyze market conditions and decide on buy/sell actions.

3. **Execute Trades**:
   - Executes trades on the Jupiter DEX aggregator based on the bot's decisions.

4. **Monitor Performance**:
   - Logs all trades and performance metrics for analysis.

---

## Example

### Running the Bot
```bash
python main.py
```

### Sample Output
```plaintext
2023-10-15 12:34:56 - INFO - Starting bot with token addresses: ['So1111111111111111111111111111111111111112', 'EPjFWdd5AufqALUs2vW0ouAZnuuzqvTZcztBbuw61zPX']
2023-10-15 12:34:57 - INFO - Fetched SOL price: $20.50
2023-10-15 12:35:00 - INFO - Buy signal detected for So1111111111111111111111111111111111111112.
2023-10-15 12:35:01 - INFO - Executed buy order for 0.1 SOL.
2023-10-15 12:40:00 - INFO - Sell signal detected for So1111111111111111111111111111111111111112.
2023-10-15 12:40:01 - INFO - Executed sell order for 0.1 SOL.
```

---

## Contributing

Contributions are welcome! If you'd like to contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Submit a pull request with a detailed description of your changes.

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## Support

If you encounter any issues or have questions, feel free to open an issue on GitHub or contact the maintainers.

---

## Acknowledgments

- **Solana**: For the blockchain infrastructure.
- **Jupiter**: For the DEX aggregator API.
- **Dexscreener**: For real-time price data.
- **Hugging Face**: For the `transformers` library used in sentiment analysis.

---

Happy trading! 🚀