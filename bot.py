import os
import json
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    ApplicationBuilder, 
    ContextTypes, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters
)

# 1. Dummy HTTP server to satisfy Render's free Web Service port checks
def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

# Start dummy HTTP server in a separate thread before launching Telegram polling
threading.Thread(target=run_dummy_server, daemon=True).start()

# 2. Bot Configuration
BOT_TOKEN = "8824798747:AAEyWTfn20Qn24FoumWwb5Fskfhn88_vU4g"
WEB_APP_URL = "https://Nahom1creator.github.io/Easy-Travel_bot/?v=14"
ADMIN_TELEGRAM_ID = 8137351651  # Your numeric Admin Telegram ID
TELEBIRR_NUMBER = "+251922821774"

# Memory tracking database for submitted bids
bids_db = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rich welcome message with travel showcase."""
    keyboard = [
        [InlineKeyboardButton("✈️ Launch Easy Travel Auction", web_app=WebAppInfo(url=WEB_APP_URL))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🌟 **Welcome to Easy Travel Bot!** 🌍✈️\n\n"
        "Experience Ethiopia's premier **Lowest Unique Bid Travel Auction**!\n\n"
        "🇪🇹 **Local Cultural Destinations:**\n"
        "• Hawassa, Adama, Harar, Wenchi, Djibouti\n"
        "• 1 Person: **70 ETB** | 2 People: **100 ETB** | 3+ People: **300 ETB**\n\n"
        "🌍 **International Flight Destinations:**\n"
        "• Dubai, Seychelles, Bangkok, Thailand, Nairobi\n"
        "• 1 Person: **300 ETB** | 2 People: **450 ETB** | 3+ People: **550 ETB**\n\n"
        "📌 *Bids must be 3 digits or less (max 999 ETB). Tap below to enter your bid!*"
    )

    await update.message.reply_photo(
        photo="https://images.unsplash.com/photo-1436491865332-7a61a109cc05?auto=format&fit=crop&w=800&q=80",
        caption=welcome_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles locked bid submissions from Mini App and sends official Telebirr instructions."""
    user = update.effective_user
    try:
        data = json.loads(update.message.web_app_data.data)
        category = data.get("category")
        destination = data.get("destination")
        tier = data.get("tier")
        bid_amount = data.get("bidAmount")
        service_fee = data.get("serviceFee")
        total_payable = data.get("totalPayable")

        bids_db[user.id] = {
            "username": f"@{user.username}" if user.username else user.first_name,
            "bid": int(bid_amount),
            "bid_str": str(bid_amount),
            "category": category,
            "destination": destination,
            "tier": tier,
            "payable": total_payable,
            "status": "UNPAID ⏳"
        }

        user_msg = (
            f"🔔 **BID LOCKED IN NOTIFICATION!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 **YOUR LOCKED BID:** `{bid_amount} ETB`\n"
            f"📍 **Destination:** {destination} ({category})\n"
            f"👥 **Package Tier:** {tier}\n"
            f"⚙️ **Service Charge:** `{service_fee} ETB`\n"
            f"💵 **TOTAL TELEBIRR PAYABLE:** `{total_payable} ETB`\n"
            f"📌 **Status:** `UNPAID ⏳` (Awaiting Receipt)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📱 **TELEBIRR PAYMENT STEPS:**\n"
            f"1️⃣ Send **`{total_payable} ETB`** to Telebirr merchant number (tap to copy):\n"
            f"👉 `{TELEBIRR_NUMBER}`\n\n"
            f"2️⃣ Send screenshot of payment receipt directly to:\n"
            f"👉 **@easy_travel**\n\n"
            f"🚨 **DISQUALIFICATION WARNING:**\n"
            f"**IF YOU DO NOT SEND THE MONEY TO `{TELEBIRR_NUMBER}` AND SEND THE SCREENSHOT TO @EASY_TRAVEL, YOU ARE AUTOMATICALLY DISQUALIFIED!**\n\n"
            f"🟢 *Once verified by admin, your bid status will turn GREEN (✅)!*"
        )

        keyboard = [
            [InlineKeyboardButton("➕ Place Another New Bid", web_app=WebAppInfo(url=WEB_APP_URL))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(user_msg, reply_markup=reply_markup, parse_mode="Markdown")

        admin_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve Payment", callback_data=f"adm_app_{user.id}"),
                InlineKeyboardButton("🚫 Disqualify", callback_data=f"adm_dis_{user.id}")
            ]
        ])

        admin_alert = (
            f"🚨 **NEW LOCKED BID SUBMITTED!**\n\n"
            f"👤 **User:** {user.first_name} (@{user.username}) [ID: `{user.id}`]\n"
            f"📍 **Destination:** {destination}\n"
            f"🎯 **Locked Bid Number:** `{bid_amount} ETB`\n"
            f"💵 **Total Payable:** `{total_payable} ETB`\n"
            f"📌 **Status:** `UNPAID ⏳`"
        )

        await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID, 
            text=admin_alert, 
            reply_markup=admin_keyboard,
            parse_mode="Markdown"
        )

    except Exception as e:
        await update.message.reply_text("❌ Error processing your bid. Please try again.")

async def handle_admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin button interaction handler."""
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != ADMIN_TELEGRAM_ID:
        return

    data = query.data
    if data.startswith("adm_app_"):
        user_id = int(data.replace("adm_app_", ""))
        if user_id in bids_db:
            bids_db[user_id]["status"] = "APPROVED ✅"
            
            await query.edit_message_text(
                f"✅ **PAYMENT APPROVED** for User ID `{user_id}` ({bids_db[user_id]['username']})",
                parse_mode="Markdown"
            )
            
            approval_msg = (
                f"🟢 **STATUS: APPROVED ✅**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎉 **YOUR BID IS OFFICIALLY VERIFIED!**\n\n"
                f"📍 **Destination:** {bids_db[user_id]['destination']}\n"
                f"🎯 **Locked Bid Number:** `{bids_db[user_id]['bid_str']} ETB`\n\n"
                f"Your Telebirr payment was confirmed. When the auction ends, you will be notified if your bid is the lowest unique winner! ✈️"
            )
            await context.bot.send_message(
                chat_id=user_id,
                text=approval_msg,
                parse_mode="Markdown"
            )

    elif data.startswith("adm_dis_"):
        user_id = int(data.replace("adm_dis_", ""))
        if user_id in bids_db:
            bids_db[user_id]["status"] = "DISQUALIFIED ❌"
            await query.edit_message_text(
                f"🚫 **BID DISQUALIFIED** for User ID `{user_id}` ({bids_db[user_id]['username']})",
                parse_mode="Markdown"
            )
            await context.bot.send_message(
                chat_id=user_id,
                text="🔴 **STATUS: DISQUALIFIED ❌**\n\nYour entry was removed because no payment screenshot was received at @easy_travel.",
                parse_mode="Markdown"
            )

async def view_bids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: /view_bids"""
    if update.effective_user.id != ADMIN_TELEGRAM_ID:
        return

    if not bids_db:
        await update.message.reply_text("No bids registered yet.")
        return

    msg = "📊 **AUTOMATIC PAYMENT STATUS BOARD:**\n\n"
    for uid, info in bids_db.items():
        status_icon = "🟢 APPROVED ✅" if "APPROVED" in info['status'] else ("🔴 DISQUALIFIED ❌" if "DISQUALIFIED" in info['status'] else "🟡 UNPAID ⏳")
        msg += f"• `{uid}` | {info['username']} | {info['destination']} | Bid: `{info['bid_str']}` | Status: {status_icon}\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def calculate_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: /calculate_winner"""
    if update.effective_user.id != ADMIN_TELEGRAM_ID:
        return

    approved_bids = [info for info in bids_db.values() if "APPROVED" in info["status"]]
    if not approved_bids:
        await update.message.reply_text("No approved paid entries available yet.")
        return

    bid_counts = {}
    for entry in approved_bids:
        val = entry["bid"]
        bid_counts[val] = bid_counts.get(val, 0) + 1

    unique_bids = [val for val, count in bid_counts.items() if count == 1]
    if not unique_bids:
        await update.message.reply_text("⚠️ No unique bids found among paid entries!")
        return

    winning_val = min(unique_bids)
    winner = next(e for e in approved_bids if e["bid"] == winning_val)

    result_text = (
        f"🏆 **EASY TRAVEL AUCTION WINNER!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Winner:** {winner['username']}\n"
        f"📍 **Destination:** {winner['destination']} ({winner['category']})\n"
        f"💰 **Winning Lowest Unique Bid:** `{winner['bid_str']} ETB`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(result_text, parse_mode="Markdown")

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('view_bids', view_bids))
    application.add_handler(CommandHandler('calculate_winner', calculate_winner))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    application.add_handler(CallbackQueryHandler(handle_admin_buttons))

    print("Easy Travel Bot is running with bid locking and HTTP keep-alive...")
    application.run_polling()
