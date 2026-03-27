import asyncio
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import TELEGRAM_TOKEN, PAIRS
from analyzer import analyzer

CHAT_ID = None
bot = Bot(token=TELEGRAM_TOKEN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id

    keyboard = [
        [InlineKeyboardButton("📊 Semua Sinyal", callback_data="all_signals")],
        [InlineKeyboardButton("🎯 Pilih Pair", callback_data="choose_pair")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🤖 **AI Hyperliquid Trading Agent** sudah aktif!\n\n"
        "Pilih menu di bawah:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def choose_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan button untuk memilih satu pair"""
    keyboard = []
    for pair in PAIRS:
        # Buat button yang readable
        display_name = pair.replace("-USDC", "")
        keyboard.append([InlineKeyboardButton(display_name, callback_data=f"signal_{pair}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎯 **Pilih Pair untuk Sinyal AI:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk semua button yang diklik"""
    query = update.callback_query
    await query.answer()   # Hilangkan loading animasi

    data = query.data

    if data == "all_signals":
        await send_all_signals(update, context)
    elif data.startswith("signal_"):
        pair = data.replace("signal_", "")
        await send_single_signal(query, pair)

async def send_single_signal(query, symbol: str):
    """Kirim sinyal untuk satu pair tertentu"""
    await query.edit_message_text(f"🤖 AI sedang menganalisis **{symbol}**...")

    signal, conf, price, rsi, fr, sl, tp1, tp2, pnl1, pnl2, pnlsl = await analyzer.get_signal(symbol)

    msg = (
        f"🚨 **AI SIGNAL {symbol}**\n\n"
        f"Harga         : `${price:,.2f}`\n"
        f"Signal        : **{signal}**\n"
        f"Confidence    : **{conf}%**\n"
        f"RSI           : {rsi:.1f}\n"
        f"Funding Rate  : {fr:.4f}%\n\n"
        f"Stop Loss     : `${sl:,.2f}`\n"
        f"Take Profit 1 : `${tp1:,.2f}` (+{pnl1}%)\n"
        f"Take Profit 2 : `${tp2:,.2f}` (+{pnl2}%)\n"
        f"Loss jika SL  : **{pnlsl}%**\n\n"
        f"Leverage      : {analyzer.leverage}x"
    )

    await query.edit_message_text(msg, parse_mode='Markdown')

async def send_all_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    if not CHAT_ID and update.message:
        CHAT_ID = update.effective_chat.id

    if isinstance(update, Update) and update.message:
        await update.message.reply_text("📊 AI sedang menganalisis semua pair...")
    else:
        await update.callback_query.message.reply_text("📊 AI sedang menganalisis semua pair...")

    messages = []
    for pair in PAIRS:
        result = await analyzer.get_signal(pair)
        signal, conf, price, rsi, fr, sl, tp1, tp2, pnl1, pnl2, pnlsl = result

        msg = (
            f"**{pair}**\n"
            f"Harga : `${price:,.2f}` | Signal : **{signal}** ({conf}%)\n"
            f"SL : `${sl:,.2f}` | TP1 : `${tp1:,.2f}` (+{pnl1}%) | TP2 : `${tp2:,.2f}` (+{pnl2}%)\n"
            f"RSI : {rsi:.1f}"
        )
        messages.append(msg)
        await asyncio.sleep(0.6)

    final_text = "\n\n".join(messages)

    if isinstance(update, Update) and update.message:
        await update.message.reply_text(final_text, parse_mode='Markdown')
    else:
        await update.callback_query.message.reply_text(final_text, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ **Hyperliquid AI Trading Agent**\n"
        f"Pairs : {len(PAIRS)}\n"
        "Exchange : Hyperliquid\n"
        "Leverage : Variable\n"
        "Status : Online"
    )

# ===================== MAIN =====================
if __name__ == '__main__':
    print("🚀 AI Hyperliquid Trading Bot dengan Button sedang berjalan...")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signal", choose_pair))   # /signal = pilih pair
    application.add_handler(CommandHandler("signals", send_all_signals))
    application.add_handler(CommandHandler("status", status))

    # Handler untuk button
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_polling(drop_pending_updates=True)
