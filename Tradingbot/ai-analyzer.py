# ai_analyzer.py
# Groq LLM tanpa SDK — hanya pakai requests
import asyncio
import requests
from config import GROQ_API_KEY, GROQ_MODEL


def _build_prompt(data: dict) -> str:
    macd_status = "Bullish (MACD > Signal)" if data['macd'] > data['macd_signal'] else "Bearish (MACD < Signal)"
    bb_pos = (
        "Overbought (di atas BB Upper)" if data['price'] > data['bb_upper']
        else "Oversold (di bawah BB Lower)" if data['price'] < data['bb_lower']
        else "Di dalam Bollinger Band (normal)"
    )
    ema_trend = (
        "BULLISH (EMA9 > EMA21 > EMA50)" if data['ema9'] > data['ema21'] > data['ema50']
        else "BEARISH (EMA9 < EMA21 < EMA50)" if data['ema9'] < data['ema21'] < data['ema50']
        else "MIXED / SIDEWAYS"
    )

    return f"""
Kamu adalah analis trading profesional untuk pasar perpetual crypto di Hyperliquid.
Analisa data teknikal berikut dan berikan rekomendasi yang jelas dan actionable.

=== DATA MARKET: {data['symbol']} ===
Harga Saat Ini : ${data['price']:,}
Perubahan 24h  : {data['change_24h']}%
Volume 24h     : ${data['volume']:,}
Timeframe      : {data['timeframe']}
Leverage       : {data['leverage']}x

=== CANDLESTICK TERAKHIR ===
Open  : ${data['open']:,}
High  : ${data['high']:,}
Low   : ${data['low']:,}
Close : ${data['close']:,}

=== INDIKATOR TEKNIKAL ===
RSI (14)          : {data['rsi']} {"(Overbought >70)" if data['rsi'] > 70 else "(Oversold <30)" if data['rsi'] < 30 else "(Netral)"}
EMA Trend         : {ema_trend}
  - EMA 9         : {data['ema9']}
  - EMA 21        : {data['ema21']}
  - EMA 50        : {data['ema50']}
MACD              : {macd_status}
  - MACD          : {data['macd']}
  - Signal        : {data['macd_signal']}
  - Histogram     : {data['macd_hist']}
Bollinger Bands   : {bb_pos}
  - BB Upper      : {data['bb_upper']}
  - BB Lower      : {data['bb_lower']}
ATR (14)          : {data['atr']}

=== INSTRUKSI ===
Berikan analisa LENGKAP dalam format berikut (gunakan emoji, Bahasa Indonesia):

📊 TREND: [BULLISH / BEARISH / SIDEWAYS]
🎯 SINYAL: [LONG / SHORT / HOLD]
💪 CONFIDENCE: [angka 0-100%]

📈 ENTRY ZONE: [range harga ideal untuk masuk]
🛡️ STOP LOSS: [harga SL yang direkomendasikan]
🎯 TAKE PROFIT 1: [TP1]
🎯 TAKE PROFIT 2: [TP2]

💡 ANALISA:
[Penjelasan 3-4 kalimat tentang kondisi market berdasarkan semua indikator di atas]

⚠️ RISIKO: [LOW / MEDIUM / HIGH]
📝 CATATAN: [1 kalimat peringatan atau tips tambahan]
"""


def _call_groq_api(prompt: str) -> str:
    """
    Panggil Groq API langsung via HTTP requests.
    Tidak butuh SDK groq, tidak butuh pydantic sama sekali.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Kamu adalah analis trading crypto profesional yang berpengalaman di pasar perpetual. "
                    "Selalu berikan analisa yang objektif, detail, dan actionable. "
                    "Gunakan data teknikal yang diberikan sebagai dasar analisa. "
                    "Jawab selalu dalam Bahasa Indonesia."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 800
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if response.status_code != 200:
        raise Exception(f"Groq API error {response.status_code}: {response.text}")

    result = response.json()
    return result["choices"][0]["message"]["content"]


async def get_ai_analysis(data: dict) -> str:
    """
    Async wrapper untuk memanggil Groq API.
    Dipakai oleh telegram_bot.py
    """
    prompt = _build_prompt(data)

    try:
        result = await asyncio.to_thread(_call_groq_api, prompt)
        return result
    except Exception as e:
        return f"❌ Error AI Analysis: {str(e)}"