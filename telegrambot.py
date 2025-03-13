#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import base58
import asyncio
import time
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    AIORateLimiter,
    MessageHandler,
    filters,
)
from solders.keypair import Keypair
from solders.message import Message
from solana.rpc.api import Client
from solana.rpc.core import RPCException
from solana.rpc.types import TxOpts
from solders.transaction import Transaction
from solders.system_program import TransferParams, transfer
from solders.pubkey import Pubkey as PublicKey

# ---------------------------- Logging Configuration ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# ---------------------------- AUXILIARY FUNCTION -----------------------------
async def safe_reply_text(update: Update, text: str, reply_markup=None):
    """
    Sends a reply using update.message or update.callback_query.message,
    whichever is available.
    """
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# ---------------------------- 1. BASIC CONFIGURATION ----------------------------
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"  # Replace with your API token from BotFather
SOLANA_RPC_URL = "https://rpc.free.gsnode.io/"  # Your RPC URL (or private RPC)
CHAIN_ID = "solana"

# Global dictionaries
user_pairs = {}      # user_id -> pair address
price_alerts = {}    # user_id -> price threshold
user_wallets = {}    # user_id -> Keypair (each user must connect their wallet)
positions = {}       # user_id -> list of positions (each with the associated pair)

# Dummy DEX wallet (to simulate buy/sell transactions)
DEX_WALLET_STR = "5h2rm7GxxAbEP8cHKY1eLZ54Wb8SLF7u2SmbK7gG3J4W"  # Replace with a valid address if needed
DEX_WALLET = PublicKey(base58.b58decode(DEX_WALLET_STR))

# ---------------------------- 2. INITIALIZE CLIENTS ----------------------------
def create_solana_keypair(base58_key: str) -> Keypair:
    raw_key = base58.b58decode(base58_key)
    return Keypair.from_bytes(raw_key)

solana_client = Client(SOLANA_RPC_URL)

# ---------------------------- 3. DEX SCREENER INFO ----------------------------
def get_dexscreener_info(chain_id: str, pair_id: str) -> dict:
    url = f"https://api.dexscreener.com/latest/dex/pairs/{chain_id}/{pair_id}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if "pairs" in data and len(data["pairs"]) > 0:
            pair_info = data["pairs"][0]
            price_usd = pair_info.get("priceUsd")
            icon = pair_info.get("icon")
            return {"price": float(price_usd) if price_usd else None, "icon": icon}
        else:
            return {}
    except Exception as e:
        logging.error(f"[Error] get_dexscreener_info: {e}")
        return {}

# ---------------------------- 4. BLOCKCHAIN TRANSACTION FUNCTIONS ----------------------------
def execute_buy_transaction(amount: float, user_kp: Keypair) -> dict:
    instruction = transfer(
        TransferParams(
            from_pubkey=user_kp.pubkey(),
            to_pubkey=DEX_WALLET,
            lamports=int(amount * 1e9)
        )
    )
    try:
        resp = solana_client.get_latest_blockhash()
        recent_blockhash = resp.value.blockhash
        msg = Message(instructions=[instruction], payer=user_kp.pubkey())
        tx = Transaction(message=msg, recent_blockhash=recent_blockhash, from_keypairs=[user_kp])
        result = solana_client.send_transaction(tx, opts=TxOpts(skip_preflight=True))
        signature = result.value  # Access signature via result.value
        logging.info(f"[Info] execute_buy_transaction: signature={signature}")
        return {"status": "ok", "signature": signature, "error": None}
    except Exception as e:
        err_str = str(e).lower()
        if "insufficient funds" in err_str:
            user_friendly = "💸 Insufficient funds for purchase."
        else:
            user_friendly = f"❌ Error during purchase: {e}"
        logging.error(f"[Error] execute_buy_transaction: {e}")
        return {"status": "error", "signature": None, "error": user_friendly}

def execute_sell_transaction(amount: float, user_kp: Keypair) -> dict:
    instruction = transfer(
        TransferParams(
            from_pubkey=user_kp.pubkey(),
            to_pubkey=DEX_WALLET,
            lamports=int(amount * 1e9)
        )
    )
    try:
        resp = solana_client.get_latest_blockhash()
        recent_blockhash = resp.value.blockhash
        msg = Message(instructions=[instruction], payer=user_kp.pubkey())
        tx = Transaction(message=msg, recent_blockhash=recent_blockhash, from_keypairs=[user_kp])
        result = solana_client.send_transaction(tx, opts=TxOpts(skip_preflight=True))
        signature = result.value
        logging.info(f"[Info] execute_sell_transaction: signature={signature}")
        return {"status": "ok", "signature": signature, "error": None}
    except Exception as e:
        err_str = str(e).lower()
        if "insufficient funds" in err_str:
            user_friendly = "💸 Insufficient funds for sale."
        else:
            user_friendly = f"❌ Error during sale: {e}"
        logging.error(f"[Error] execute_sell_transaction: {e}")
        return {"status": "error", "signature": None, "error": user_friendly}

# ---------------------------- 5. UTILITY FUNCTIONS ----------------------------
def get_balance_solana(pubkey: PublicKey) -> float:
    try:
        balance_lamports = solana_client.get_balance(pubkey)["result"]["value"]
        return balance_lamports / 1e9
    except (RPCException, KeyError):
        return 0.0

# ---------------------------- 6. MAIN MENU WITH BUTTONS ----------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_wallets:
        wallet_status = f"🟢 {str(user_wallets[user_id].pubkey())[:7]}"
    else:
        wallet_status = "🔴 (Wallet not connected)"
    keyboard = [
        [InlineKeyboardButton("🔗 Connect Wallet", callback_data="menu_connectwallet"),
         InlineKeyboardButton("🔧 Set Pair", callback_data="menu_setpair")],
        [InlineKeyboardButton("💵 Buy", callback_data="menu_buy"),
         InlineKeyboardButton("📉 Sell", callback_data="menu_sell")],
        [InlineKeyboardButton("💰 Balance", callback_data="menu_balance"),
         InlineKeyboardButton("📊 Positions", callback_data="menu_positions")],
        [InlineKeyboardButton("🚨 Alert", callback_data="menu_alert")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await safe_reply_text(update, 
        f"*Hello! I'm your Solana Trading Bot.*\n\nWallet: {wallet_status}\n\n_Select an option:_",
        reply_markup=reply_markup
    )

# ---------------------------- 7. MAIN MENU HANDLER ----------------------------
async def handle_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "menu_connectwallet":
        await query.message.reply_text("Please enter your private key (base58 format):")
        context.user_data["awaiting_connectwallet"] = True
    elif data == "menu_setpair":
        await query.message.reply_text("Please enter the token pair (DexScreener Token Address):")
        context.user_data["awaiting_setpair"] = True
    elif data == "menu_buy":
        await buy_command(update, context)
    elif data == "menu_sell":
        await sell_command(update, context)
    elif data == "menu_balance":
        await balance_command(update, context)
    elif data == "menu_positions":
        await positions_command(update, context)
    elif data == "menu_alert":
        await query.message.reply_text("Please enter the alert price:")
        context.user_data["awaiting_alert"] = True

# ---------------------------- 8. TRADITIONAL COMMANDS ----------------------------
async def connectwallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await safe_reply_text(update, "Please enter your private key (base58 format):")
        context.user_data["awaiting_connectwallet"] = True
        return
    pk_base58 = context.args[0]
    try:
        new_kp = Keypair.from_bytes(base58.b58decode(pk_base58))
        user_wallets[update.effective_user.id] = new_kp
        pubkey_str = str(new_kp.pubkey())
        await safe_reply_text(update, f"✅ Wallet connected!\nWallet: 🟢 {pubkey_str[:7]}...")
    except Exception as e:
        await safe_reply_text(update, f"❌ Error connecting wallet: {e}")
    await start_command(update, context)

async def setpair_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await safe_reply_text(update, "Usage: /setpair <pairAddress>")
        return
    pair_id = context.args[0]
    user_pairs[update.effective_user.id] = pair_id
    await safe_reply_text(update, f"✅ Pair set to: `{pair_id}`\n")
    await start_command(update, context)

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_pairs:
        await safe_reply_text(update, "You haven't set a pair yet. Use /setpair first.")
        return
    pair_id = user_pairs[user_id]
    info = get_dexscreener_info(CHAIN_ID, pair_id)
    if info and info.get("price") is not None:
        text = f"*Current price for {pair_id}:*\n💲 `{info['price']:.6f} USD`"
        await safe_reply_text(update, text)
        if info.get("icon"):
            try:
                if update.message:
                    await update.message.reply_photo(photo=info["icon"])
                elif update.callback_query and update.callback_query.message:
                    await update.callback_query.message.reply_photo(photo=info["icon"])
            except Exception as e:
                logging.error(f"[Error] Sending token icon: {e}")
    else:
        await safe_reply_text(update, "Could not retrieve price or icon. Is the pair correct?")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_wallets:
        await safe_reply_text(update, "You don't have a connected wallet. Use /connectwallet")
        return
    kp = user_wallets[user_id]
    bal = get_balance_solana(kp.pubkey())
    await safe_reply_text(update, f"*Your Wallet Balance:*\n💰 `{kp.pubkey()}`:\n`{bal} SOL`")

async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in positions or not positions[user_id]:
        await safe_reply_text(update, "You have no open positions.")
        return
    if user_id not in user_pairs:
        await safe_reply_text(update, "No pair set for PnL calculation.")
        return
    current_pair = user_pairs[user_id]
    filtered_positions = [pos for pos in positions[user_id] if pos.get("pair", current_pair) == current_pair]
    if not filtered_positions:
        await safe_reply_text(update, "No open positions for the current pair.")
        return
    current_price = get_dexscreener_info(CHAIN_ID, current_pair).get("price")
    msg = f"*📊 Positions for {current_pair}:*\n\n"
    total_pnl = 0.0
    for pos in filtered_positions:
        pnl = (current_price - pos["purchase_price"]) * pos["amount"]
        total_pnl += pnl
        purchase_time = time.strftime("🕒 %Y-%m-%d %H:%M:%S", time.localtime(pos["timestamp"]))
        msg += (f"• *Purchase:* `{pos['amount']} SOL` at 💲`{pos['purchase_price']:.6f} USD`\n"
                f"  {purchase_time}\n"
                f"  *Signature:* `{pos['signature']}`\n"
                f"  *PnL:* `{pnl:.2f} USD`\n\n")
    msg += f"👉 *Total PnL:* `{total_pnl:.2f} USD`"
    await safe_reply_text(update, msg)

async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await safe_reply_text(update, "Usage: /alert <price>")
        return
    try:
        threshold = float(context.args[0])
        user_id = update.effective_user.id
        price_alerts[user_id] = threshold
        await safe_reply_text(update, f"🚨 Alert set: I'll notify you when the price exceeds 💲{threshold} USD.")
    except ValueError:
        await safe_reply_text(update, "Invalid price. Please try /alert again.")

# ---------------------------- 9. BUY/SELL HANDLERS (BUTTONS) ----------------------------
async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_wallets:
        await safe_reply_text(update, "You must connect your wallet with /connectwallet before buying.")
        return
    keyboard = [
        [InlineKeyboardButton("💵 0.1 SOL", callback_data="buy_0.1"),
         InlineKeyboardButton("💵 0.3 SOL", callback_data="buy_0.3")],
        [InlineKeyboardButton("💵 0.5 SOL", callback_data="buy_0.5"),
         InlineKeyboardButton("💵 1 SOL", callback_data="buy_1")],
        [InlineKeyboardButton("✏️ Custom", callback_data="buy_custom")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await safe_reply_text(update, "Select an amount to buy:", reply_markup=reply_markup)

async def sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_wallets:
        await safe_reply_text(update, "You must connect your wallet with /connectwallet before selling.")
        return
    keyboard = [
        [InlineKeyboardButton("📉 10 tokens", callback_data="sell_10"),
         InlineKeyboardButton("📉 50 tokens", callback_data="sell_50")],
        [InlineKeyboardButton("📉 100 tokens", callback_data="sell_100"),
         InlineKeyboardButton("📉 500 tokens", callback_data="sell_500")],
        [InlineKeyboardButton("🚀 Sell All", callback_data="sell_all"),
         InlineKeyboardButton("✏️ Custom", callback_data="sell_custom")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await safe_reply_text(update, "Select an amount to sell:", reply_markup=reply_markup)

async def handle_buy_sell_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if user_id not in user_wallets:
        await query.message.reply_text("You must connect your wallet with /connectwallet before operating.")
        return

    user_kp = user_wallets[user_id]

    if data.startswith("buy_"):
        if data == "buy_custom":
            await query.message.reply_text("Enter the amount of SOL to buy (e.g., 0.25):")
            context.user_data["awaiting_buy_custom"] = True
            return
        else:
            amount = float(data.split("_")[1])
            current_price = get_dexscreener_info(CHAIN_ID, user_pairs.get(user_id, "")).get("price", 0.0) if user_id in user_pairs else 0.0
            result_dict = execute_buy_transaction(amount, user_kp)
            if result_dict["status"] == "error":
                await query.message.reply_text(f"❌ {result_dict['error']}")
                return
            pos = {
                "amount": amount,
                "purchase_price": current_price,
                "signature": result_dict["signature"],
                "timestamp": time.time(),
                "pair": user_pairs.get(user_id, "")
            }
            positions.setdefault(user_id, []).append(pos)
            await query.message.reply_text(
                f"✅ Purchase executed:\nAmount: {amount} SOL\nSignature: `{result_dict['signature']}`\nWallet: `{user_kp.pubkey()}`"
            )

    elif data.startswith("sell_"):
        if data == "sell_custom":
            await query.message.reply_text("Enter the number of tokens to sell (e.g., 25):")
            context.user_data["awaiting_sell_custom"] = True
            return
        elif data == "sell_all":
            current_pair = user_pairs.get(user_id, "")
            total_amount = sum(pos["amount"] for pos in positions.get(user_id, []) if pos.get("pair", current_pair) == current_pair)
            if total_amount == 0:
                await query.message.reply_text("You have no tokens to sell for the current pair.")
                return
            result_dict = execute_sell_transaction(total_amount, user_kp)
            if result_dict["status"] == "error":
                await query.message.reply_text(f"❌ {result_dict['error']}")
                return
            positions[user_id] = [pos for pos in positions.get(user_id, []) if pos.get("pair", current_pair) != current_pair]
            await query.message.reply_text(
                f"🚀 Sell All executed:\nAmount: {total_amount} tokens\nSignature: `{result_dict['signature']}`\nWallet: `{user_kp.pubkey()}`"
            )
        else:
            amount = float(data.split("_")[1])
            result_dict = execute_sell_transaction(amount, user_kp)
            if result_dict["status"] == "error":
                await query.message.reply_text(f"❌ {result_dict['error']}")
                return
            await query.message.reply_text(
                f"✅ Sale executed:\nAmount: {amount} tokens\nSignature: `{result_dict['signature']}`\nWallet: `{user_kp.pubkey()}`"
            )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    user_id = update.effective_user.id

    if context.user_data.get("awaiting_connectwallet"):
        context.user_data["awaiting_connectwallet"] = False
        try:
            new_kp = Keypair.from_bytes(base58.b58decode(user_text))
            user_wallets[user_id] = new_kp
            pubkey_str = str(new_kp.pubkey())
            await update.message.reply_text(f"✅ Wallet connected!\nWallet: 🟢 {pubkey_str[:7]}...")
        except Exception as e:
            await update.message.reply_text(f"Error connecting wallet: {e}")
        await start_command(update, context)
        return

    if context.user_data.get("awaiting_setpair"):
        context.user_data["awaiting_setpair"] = False
        user_pairs[user_id] = user_text
        await update.message.reply_text(f"✅ Pair set to: `{user_text}`")
        await start_command(update, context)
        return

    if context.user_data.get("awaiting_alert"):
        context.user_data["awaiting_alert"] = False
        try:
            threshold = float(user_text)
            price_alerts[user_id] = threshold
            await update.message.reply_text(f"🚨 Alert set: I'll notify you when the price exceeds 💲{threshold} USD.")
        except ValueError:
            await update.message.reply_text("Invalid price. Try /alert again.")
        return

    if context.user_data.get("awaiting_buy_custom"):
        context.user_data["awaiting_buy_custom"] = False
        try:
            amount = float(user_text)
            current_price = get_dexscreener_info(CHAIN_ID, user_pairs.get(user_id, "")).get("price", 0.0) if user_id in user_pairs else 0.0
            result_dict = execute_buy_transaction(amount, user_wallets[user_id])
            if result_dict["status"] == "error":
                await update.message.reply_text(f"❌ {result_dict['error']}")
                return
            pos = {
                "amount": amount,
                "purchase_price": current_price,
                "signature": result_dict["signature"],
                "timestamp": time.time(),
                "pair": user_pairs.get(user_id, "")
            }
            positions.setdefault(user_id, []).append(pos)
            await update.message.reply_text(
                f"✅ Purchase executed:\nAmount: {amount} SOL\nSignature: `{result_dict['signature']}`\nWallet: `{user_wallets[user_id].pubkey()}`"
            )
        except ValueError:
            await update.message.reply_text("Invalid amount. Try /buy again.")
        return

    if context.user_data.get("awaiting_sell_custom"):
        context.user_data["awaiting_sell_custom"] = False
        try:
            amount = float(user_text)
            result_dict = execute_sell_transaction(amount, user_wallets[user_id])
            if result_dict["status"] == "error":
                await update.message.reply_text(f"❌ {result_dict['error']}")
                return
            await update.message.reply_text(
                f"✅ Sale executed:\nAmount: {amount} tokens\nSignature: `{result_dict['signature']}`\nWallet: `{user_wallets[user_id].pubkey()}`"
            )
        except ValueError:
            await update.message.reply_text("Invalid amount. Try /sell again.")
        return

# ---------------------------- 10. PRICE ALERT JOB ----------------------------
async def price_watcher(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    for user_id, threshold in list(price_alerts.items()):
        if user_id not in user_pairs:
            continue
        pair_id = user_pairs[user_id]
        info = get_dexscreener_info(CHAIN_ID, pair_id)
        price = info.get("price")
        if price and price >= threshold:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=f"🚨 *ALERT!* The price for {pair_id} reached 💲{price:.6f} (threshold {threshold} USD).",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"[Error] Sending alert: {e}")

# ---------------------------- 11. RUN THE APPLICATION ----------------------------
def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .rate_limiter(AIORateLimiter(overall_max_rate=20, overall_time_period=1.0))
        .build()
    )

    # Traditional commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("connectwallet", connectwallet_command))
    app.add_handler(CommandHandler("setpair", setpair_command))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("sell", sell_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("alert", alert_command))
    app.add_handler(CommandHandler("positions", positions_command))

    # Callback for main menu buttons
    app.add_handler(CallbackQueryHandler(handle_main_menu_callback, pattern="^menu_"))
    # Callback for buy/sell buttons
    app.add_handler(CallbackQueryHandler(handle_buy_sell_callback, pattern="^(buy_|sell_)"))

    # Message handler for interactive flows
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Price alert job
    app.job_queue.run_repeating(price_watcher, interval=60, first=0)

    logging.info("[Bot] Starting Telegram bot (python-telegram-bot v20+)...")
    app.run_polling()

if __name__ == "__main__":
    main()
