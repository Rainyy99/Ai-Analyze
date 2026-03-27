import ccxt
import pandas as pd
import asyncio
from config import PAIRS, TIMEFRAME, LIMIT

class TechnicalAnalyzer:
    def __init__(self):
        self.exchange = ccxt.hyperliquid({
            'enableRateLimit': True,
            'timeout': 40000,
        })
        self.leverage = 20
        self.markets_loaded = False

    async def get_signal(self, symbol: str):
        try:
            if not self.markets_loaded:
                print("Loading Hyperliquid markets...")
                await asyncio.to_thread(self.exchange.load_markets)
                self.markets_loaded = True

            # === Ambil Harga Real-Time (ini yang paling penting) ===
            ticker = await asyncio.to_thread(self.exchange.fetch_ticker, symbol)
            price = float(ticker['last'])          # Harga terakhir (real-time)

            # === Ambil OHLCV hanya untuk indikator (EMA, RSI, ATR) ===
            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv, symbol, TIMEFRAME, limit=LIMIT
            )

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Indikator
            df['ema9']  = df['close'].ewm(span=9,  adjust=False).mean()
            df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
            df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

            latest = df.iloc[-1]
            rsi = float(latest.get('rsi', 50.0))

            # Signal Logic
            ema_bull = (latest['ema9'] > latest['ema21'] > latest['ema50']) if not pd.isna(latest.get('ema50')) else False

            if ema_bull and 40 < rsi < 75:
                signal = "🟢 LONG"
                confidence = 82
                direction = "long"
            elif not ema_bull and 25 < rsi < 60:
                signal = "🔴 SHORT"
                confidence = 80
                direction = "short"
            else:
                signal = "⚪ HOLD"
                confidence = 40
                direction = "hold"

            # SL & TP berdasarkan ATR
            atr = self.calculate_atr(df)
            if direction == "long":
                sl = price - (atr * 1.5)
                tp1 = price + (atr * 2.0)
                tp2 = price + (atr * 4.0)
            elif direction == "short":
                sl = price + (atr * 1.5)
                tp1 = price - (atr * 2.0)
                tp2 = price - (atr * 4.0)
            else:
                sl = tp1 = tp2 = price

            # P&L
            if direction == "long":
                pnl_tp1 = ((tp1 - price) / price) * self.leverage * 100
                pnl_tp2 = ((tp2 - price) / price) * self.leverage * 100
                pnl_sl  = ((sl - price) / price) * self.leverage * 100
            elif direction == "short":
                pnl_tp1 = ((price - tp1) / price) * self.leverage * 100
                pnl_tp2 = ((price - tp2) / price) * self.leverage * 100
                pnl_sl  = ((price - sl) / price) * self.leverage * 100
            else:
                pnl_tp1 = pnl_tp2 = pnl_sl = 0.0

            funding_rate = 0.0

            return (
                signal, confidence, price, rsi, funding_rate,
                round(sl, 2), round(tp1, 2), round(tp2, 2),
                round(pnl_tp1, 1), round(pnl_tp2, 1), round(pnl_sl, 1)
            )

        except Exception as e:
            print(f"Error pada {symbol}: {e}")
            return "ERROR", 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    def calculate_atr(self, df, period=14):
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return float(atr.iloc[-1]) if len(atr) > 0 and not pd.isna(atr.iloc[-1]) else (df['close'].iloc[-1] * 0.02)


analyzer = TechnicalAnalyzer()
