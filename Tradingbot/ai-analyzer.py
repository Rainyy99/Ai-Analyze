# ai_analyzer.py - Module khusus untuk analisa AI menggunakan Groq

from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY)

def analyze_market_with_ai(symbol: str, market_data: dict) -> str:
    """
    Mengirim data market ke Groq LLM dan mendapatkan analisa AI.
    
    Args:
        symbol: Nama coin, contoh "BTC", "ETH"
        market_data: Dictionary berisi data OHLCV, indikator teknikal, dll
    
    Returns:
        String berisi analisa AI dari Groq
    """
    
    # Buat prompt dari data market
    prompt = f"""
Kamu adalah analis trading crypto profesional yang ahli di pasar perpetual Hyperliquid.
Analisa data berikut dan berikan rekomendasi trading yang jelas.

=== DATA MARKET {symbol}/USDT ===
Harga Sekarang: ${market_data.get('price', 'N/A')}
Volume 24h: {market_data.get('volume', 'N/A')}
Perubahan 24h: {market_data.get('change_24h', 'N/A')}%

=== INDIKATOR TEKNIKAL ===
RSI (14): {market_data.get('rsi', 'N/A')}
EMA 20: {market_data.get('ema_20', 'N/A')}
EMA 50: {market_data.get('ema_50', 'N/A')}
MACD: {market_data.get('macd', 'N/A')}
MACD Signal: {market_data.get('macd_signal', 'N/A')}
Bollinger Band Atas: {market_data.get('bb_upper', 'N/A')}
Bollinger Band Bawah: {market_data.get('bb_lower', 'N/A')}

=== CANDLE TERAKHIR ===
Open: {market_data.get('open', 'N/A')}
High: {market_data.get('high', 'N/A')}
Low: {market_data.get('low', 'N/A')}
Close: {market_data.get('close', 'N/A')}

Berikan analisa dalam format berikut:
📊 TREND: [BULLISH/BEARISH/SIDEWAYS]
🎯 SINYAL: [BUY/SELL/HOLD]
💡 ALASAN: [Penjelasan singkat 2-3 kalimat]
🛡️ STOP LOSS: [Level harga]
🎯 TAKE PROFIT: [Level harga]
⚠️ RISIKO: [LOW/MEDIUM/HIGH]
"""
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Kamu adalah analis trading crypto profesional. Selalu berikan analisa yang objektif, ringkas, dan actionable. Gunakan Bahasa Indonesia."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.3,  # Lebih rendah = lebih konsisten
            max_tokens=500,
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"❌ Error AI Analysis: {str(e)}"


def get_market_sentiment(coins_data: list) -> str:
    """
    Analisa sentiment keseluruhan market dari multiple coins.
    
    Args:
        coins_data: List of dict berisi data beberapa coin
    
    Returns:
        String berisi sentiment market secara keseluruhan
    """
    
    coins_summary = "\n".join([
        f"- {c['symbol']}: ${c.get('price','?')} | RSI: {c.get('rsi','?')} | Change: {c.get('change_24h','?')}%"
        for c in coins_data
    ])
    
    prompt = f"""
Analisa sentiment market crypto secara keseluruhan dari data berikut:

{coins_summary}

Berikan ringkasan sentiment dalam format:
🌡️ SENTIMENT MARKET: [BULLISH/BEARISH/NEUTRAL]
📈 COINS KUAT: [daftar coin dengan sinyal kuat]
📉 COINS LEMAH: [daftar coin dengan sinyal lemah]
💬 KESIMPULAN: [1-2 kalimat ringkasan]
"""
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Kamu adalah analis market crypto profesional. Jawab dalam Bahasa Indonesia."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300,
        )
        return response.choices[0].message.content
        
    except Exception as e:
        return f"❌ Error Sentiment Analysis: {str(e)}"