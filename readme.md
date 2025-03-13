# Solana Trading Bot for Telegram

Welcome to the Solana Trading Bot! This project allows you to build and run your very own Telegram trading bot for the Solana blockchain. 

Whether you're completely new to programming or just starting out in blockchain, this step-by-step guide will help you set up Visual Studio Code with Python, create your bot using BotFather (including setting a custom profile picture), create a virtual environment, install the required libraries, configure the code, run your bot in your terminal, and finally interact with your bot on Telegram. 

---

## Repository Structure

solana-trading-bot/
├── README.md
├── requirements.txt
└── telegrambot.py

---

## Features

- **Connect Your Wallet:** Securely connect your personal Solana wallet using your private key (Base58 format).
- **Set Token Pair:** Choose a token pair (DexScreener token address) to monitor and trade.
- **Real-Time Price Data:** Retrieve current token prices and token icons from DexScreener.
- **Buy & Sell Tokens:** Execute buy and sell transactions with fixed amounts, custom values, or use a "Sell All" option.
- **View Balance and Positions:** Check your wallet balance and view detailed information about your open positions and profit/loss (PnL).
- **Price Alerts:** Set up alerts to be notified when the token price exceeds a specified threshold.
- **Interactive UI:** Enjoy an intuitive interface with inline keyboards, Markdown formatting, emojis, and dynamic images.
- **Enhanced Logging:** Benefit from advanced error logging using Python’s logging module.

---

## 1. Install Visual Studio Code and Python

Before you start coding, ensure you have Visual Studio Code (VSCode) and Python installed:

- **Download VSCode:** [https://code.visualstudio.com/](https://code.visualstudio.com/)
- **Download Python:** [https://www.python.org/downloads/](https://www.python.org/downloads/)  
  *Tip: Make sure to select "Add Python to PATH" during installation.*

![install dependencies](https://github.com/user-attachments/assets/27db1e0f-18bb-4b19-aa75-af33b0c184db)


---

## 2. Create Your Telegram Bot with BotFather

Before writing any code, you need to create your Telegram bot via BotFather.

### Steps:

1. **Open Telegram and Start a Chat with BotFather:**  
   Search for **BotFather** in Telegram and start a conversation.

2. **Create a New Bot:**  
   Type `/newbot` and follow the prompts:
   - **Name Your Bot:** (e.g., *SolanaTraderBot*)
   - **Choose a Username:** Must end with "bot" (e.g., *SolanaTraderBot*)
   BotFather will provide you with an API token. **Copy this token** for later.

3. **Set a Profile Picture:**  
   To personalize your bot, type `/setuserpic` and follow the instructions to upload a custom image.

![creating the bot with bot father](https://github.com/user-attachments/assets/1765a278-8651-4fd9-8865-7156bf745ff5)


---

## 3. Set Up Your Project in Visual Studio Code

### a. Create a New Folder and Open It in VSCode

Create a folder on your computer and open it in VSCode.

### b. Create a Virtual Environment

1. Open the integrated terminal in VSCode (press `` Ctrl+` ``).
2. Run:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

### c. Install the Required Libraries

Create a file named requirements.txt with the following content:

```bash
python-telegram-bot==20.11.1
requests
base58
solana
```

Then, in the terminal run:

```bash
pip install -r requirements.txt
```

---

## 4. Configure the Bot Code

Create a file named telegrambot.py in your VSCode project and paste the code below. Then, update the following configuration values:
	•	TELEGRAM_BOT_TOKEN: Replace "YOUR_TELEGRAM_BOT_TOKEN_HERE" with the API token from BotFather.
	•	SOLANA_RPC_URL: Enter your preferred Solana RPC endpoint.
	•	CHAIN_ID: It is set to "solana" by default.
	•	DEX_WALLET_STR: (Optional) Replace with a valid dummy wallet address for simulation.

---

## 5. Run the Bot

In the VSCode terminal, run:

```bash
python telegrambot.py
```

Your bot will start polling for updates. Open Telegram and search for your bot by its username. You’ll see the main menu with interactive buttons.

---

## 6. How the Bot Works

<img width="612" alt="Captura de pantalla 2025-03-12 a la(s) 21 17 16" src="https://github.com/user-attachments/assets/7d13f0d1-991f-47f3-9901-463dee102b9e" />

### /start
	•	Purpose: Displays the main menu with interactive buttons.
	•	Details: The main menu includes buttons for Connect Wallet, Set Pair, Buy, Sell, Balance, Positions, and Alert.

### /connectwallet
	•	Purpose: Connect your personal Solana wallet.
	•	Details: You can either type /connectwallet <your_private_key> directly or tap the Connect Wallet button. The bot will prompt you to enter your private key (Base58 format) and then update the main menu with a green wallet icon when successful.

### /setpair
	•	Purpose: Set the token pair to trade.
	•	Details: Enter /setpair <token_pair_address> or use the Set Pair button. The bot stores the pair, which is used for retrieving price data and associating all your trading positions.

### /price
	•	Purpose: Retrieve current price and token icon.
	•	Details: When you type /price, the bot fetches the current token price from DexScreener. If available, it also sends the token icon as an image, improving the UI.

### /buy
	•	Purpose: Execute a buy transaction.
	•	Details: The Buy command presents a grid of inline buttons with fixed amounts (e.g., 0.1 SOL, 0.3 SOL, etc.) and an option for a custom amount. After executing a buy, the bot logs the trade and sends a confirmation message with the transaction signature.

### /sell 
	•	Purpose: Execute a sell transaction.
	•	Details: The Sell command similarly shows fixed amounts, a custom option, and a Sell All button that sells all tokens for the current pair. The bot confirms the sale and clears positions if “Sell All” is selected.

### /balance
	•	Purpose: Check your wallet balance.
	•	Details: Typing /balance returns a message showing your wallet address and current SOL balance.

### /positions
	•	Purpose: Display open positions for the current pair.
	•	Details: The bot filters positions by the token pair you have set and displays detailed trade information, including purchase price, time, transaction signature, and profit/loss (PnL).

### /alert
	•	Purpose: Set a price alert.
	•	Details: Using /alert <price> sets a threshold. The bot monitors the price and sends you a notification when it exceeds this value.

![photo_2025-02-19 23 06 36](https://github.com/user-attachments/assets/c76cbf91-3df4-4c2b-ac52-523e3167b1ce)
(https://discord.gg/SvUCmXNC)

 ---
 ## 7. Final Thoughts
 
This guide walked you through every step needed to build your own Telegram trading bot for Solana:
	•	Installing VSCode and Python
	•	Creating your Telegram bot with BotFather and setting a custom profile picture
	•	Setting up a virtual environment and installing required libraries
	•	Configuring and running the bot in VSCode
	•	Interacting with your bot on Telegram using a professional and interactive interface

Simply copy and paste the code in *telegrambot.py* into your telegrambot.py file, update the configuration values, and run the bot from your terminal. Enjoy trading on Solana with your new Telegram bot!

