import asyncio
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import TELEGRAM_TOKEN, PAIRS
from analyzer import analyzer
from ai_analyzer import get_ai_analysis   # ← IMPORT BARU

CHAT_ID = None
bot = Bot(token=TELEGRAM_TOKEN)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id

    keyboard = [
        [InlineKeyboardButton("📊 Semua Sinyal", callback_data="all_signals")],
        [InlineKeyboardButton("🎯 Pilih Pair", callback_data="choose_pair")],
        [InlineKeyboardButton("🤖 AI Analyze", callback_data="choose_ai")],  # ← BARU
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🤖 **AI Hyperliquid Trading Agent** sudah aktif!\n\n"
        "Pilih menu di bawah:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def choose_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for pair in PAIRS:
        display_name = pair.replace("-USDC", "")
        keyboard.append([InlineKeyboardButton(display_name, callback_data=f"signal_{pair}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎯 **Pilih Pair untuk Sinyal AI:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "all_signals":
        await send_all_signals(update, context)

    elif data == "choose_pair":
        # Tampilkan pilihan pair untuk sinyal biasa
        keyboard = []
        for pair in PAIRS:
            display_name = pair.replace("/USDC", "").replace("/USDT", "")
            keyboard.append([InlineKeyboardButton(display_name, callback_data=f"signal_{pair}")])
        await query.edit_message_text(
            "🎯 **Pilih Pair untuk Sinyal:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif data == "choose_ai":
        # ← BARU: Tampilkan pilihan pair untuk AI analysis
        keyboard = []
        for pair in PAIRS:
            display_name = pair.replace("/USDC", "").replace("/USDT", "")
            keyboard.append([InlineKeyboardButton(f"🤖 {display_name}", callback_data=f"ai_{pair}")])
        keyboard.append([InlineKeyboardButton("🤖 Analisa Semua Pair", callback_data="ai_all")])
        await query.edit_message_text(
            "🤖 **Pilih Pair untuk AI LLM Analysis:**\n"
            "_AI akan menganalisa semua indikator teknikal secara mendalam_",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif data.startswith("signal_"):
        pair = data.replace("signal_", "")
        await send_single_signal(query, pair)

    elif data.startswith("ai_") and data != "ai_all":
        # ← BARU: Kirim AI analysis untuk pair tertentu
        pair = data.replace("ai_", "")
        await send_ai_signal(query, pair)

    elif data == "ai_all":
        # ← BARU: Kirim AI analysis untuk semua pair
        await send_all_ai_signals(query)


async def send_single_signal(query, symbol: str):
    """Kirim sinyal teknikal biasa (existing)."""
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


# ================================================================
# FUNGSI BARU: AI LLM Analysis
# ================================================================

async def send_ai_signal(query, symbol: str):
    """Kirim analisa mendalam dari Groq LLM untuk satu pair."""
    await query.edit_message_text(
        f"🤖 **AI LLM sedang menganalisis {symbol}...**\n\n"
        f"⏳ Mengambil data market & indikator...",
        parse_mode='Markdown'
    )

    # Ambil data mentah
    raw_data = await analyzer.get_raw_data(symbol)

    if not raw_data:
        await query.edit_message_text(
            f"❌ Gagal mengambil data untuk **{symbol}**.\n"
            f"Pastikan symbol benar dan Hyperliquid dapat diakses.",
            parse_mode='Markdown'
        )
        return

    await query.edit_message_text(
        f"🧠 **Data diterima. AI LLM sedang menganalisa...**\n\n"
        f"⏳ Mengirim ke Groq LLM...",
        parse_mode='Markdown'
    )

    # Kirim ke Groq LLM
    ai_result = await get_ai_analysis(raw_data)

    # Header + hasil AI
    header = (
        f"🤖 **AI LLM ANALYSIS — {symbol}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Harga: `${raw_data['price']:,}` | RSI: {raw_data['rsi']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    full_msg = header + ai_result

    # Telegram max 4096 karakter per pesan
    if len(full_msg) > 4096:
        full_msg = full_msg[:4090] + "\n..."

    await query.edit_message_text(full_msg, parse_mode='Markdown')


async def send_all_ai_signals(query):
    """Kirim AI LLM analysis untuk semua pair satu per satu."""
    await query.edit_message_text(
        "🤖 **AI LLM Analysis — Semua Pair**\n\n"
        "⏳ Proses ini memakan waktu ~10-30 detik per pair...",
        parse_mode='Markdown'
    )

    chat_id = query.message.chat_id

    for pair in PAIRS:
        try:
            # Update status
            await bot.send_message(
                chat_id=chat_id,
                text=f"⏳ Menganalisa **{pair}** dengan AI LLM...",
                parse_mode='Markdown'
            )

            raw_data = await analyzer.get_raw_data(pair)
            if not raw_data:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Gagal ambil data **{pair}**",
                    parse_mode='Markdown'
                )
                continue

            ai_result = await get_ai_analysis(raw_data)

            header = (
                f"🤖 **AI LLM — {pair}**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 Harga: `${raw_data['price']:,}` | RSI: {raw_data['rsi']}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
            )

            full_msg = header + ai_result
            if len(full_msg) > 4096:
                full_msg = full_msg[:4090] + "\n..."

            await bot.send_message(
                chat_id=chat_id,
                text=full_msg,
                parse_mode='Markdown'
            )

            # Jeda antar pair agar tidak rate limit
            await asyncio.sleep(2)

        except Exception as e:
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ Error analisa **{pair}**: {str(e)}",
                parse_mode='Markdown'
            )

    await bot.send_message(
        chat_id=chat_id,
        text="✅ **AI LLM Analysis selesai untuk semua pair!**",
        parse_mode='Markdown'
    )


# ================================================================

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
        "Status : Online\n"
        "LLM : Groq (llama-3.3-70b)"
    )


# ===================== MAIN =====================
if __name__ == '__main__':
    print("🚀 AI Hyperliquid Trading Bot dengan Groq LLM sedang berjalan...")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signal", choose_pair))
    application.add_handler(CommandHandler("signals", send_all_signals))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_polling(drop_pending_updates=True)