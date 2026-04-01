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

            ticker = await asyncio.to_thread(self.exchange.fetch_ticker, symbol)
            price = float(ticker['last'])

            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv, symbol, TIMEFRAME, limit=LIMIT
            )

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

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

    # ============================================================
    # METHOD BARU — dipakai oleh ai_analyzer.py
    # ============================================================
    async def get_raw_data(self, symbol: str) -> dict | None:
        """
        Ambil semua data mentah (harga, indikator) dalam bentuk dict.
        Digunakan oleh AI analyzer untuk membuat analisa LLM.
        """
        try:
            if not self.markets_loaded:
                await asyncio.to_thread(self.exchange.load_markets)
                self.markets_loaded = True

            ticker = await asyncio.to_thread(self.exchange.fetch_ticker, symbol)
            price = float(ticker['last'])
            change_24h = float(ticker.get('percentage', 0.0) or 0.0)
            volume = float(ticker.get('quoteVolume', 0.0) or 0.0)

            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv, symbol, TIMEFRAME, limit=LIMIT
            )

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # EMA
            df['ema9']  = df['close'].ewm(span=9,  adjust=False).mean()
            df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
            df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

            # RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

            # Bollinger Bands
            df['bb_mid']   = df['close'].rolling(20).mean()
            df['bb_upper'] = df['bb_mid'] + (df['close'].rolling(20).std() * 2)
            df['bb_lower'] = df['bb_mid'] - (df['close'].rolling(20).std() * 2)

            # MACD
            ema12 = df['close'].ewm(span=12, adjust=False).mean()
            ema26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd']        = ema12 - ema26
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_hist']   = df['macd'] - df['macd_signal']

            atr = self.calculate_atr(df)
            latest = df.iloc[-1]

            return {
                'symbol': symbol,
                'price': round(price, 4),
                'change_24h': round(change_24h, 2),
                'volume': round(volume, 2),
                'open': round(float(latest['open']), 4),
                'high': round(float(latest['high']), 4),
                'low': round(float(latest['low']), 4),
                'close': round(float(latest['close']), 4),
                'rsi': round(float(latest['rsi']), 2),
                'ema9': round(float(latest['ema9']), 4),
                'ema21': round(float(latest['ema21']), 4),
                'ema50': round(float(latest['ema50']), 4),
                'bb_upper': round(float(latest['bb_upper']), 4),
                'bb_lower': round(float(latest['bb_lower']), 4),
                'macd': round(float(latest['macd']), 6),
                'macd_signal': round(float(latest['macd_signal']), 6),
                'macd_hist': round(float(latest['macd_hist']), 6),
                'atr': round(atr, 4),
                'leverage': self.leverage,
                'timeframe': TIMEFRAME,
            }

        except Exception as e:
            print(f"Error get_raw_data {symbol}: {e}")
            return None

    def calculate_atr(self, df, period=14):
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return float(atr.iloc[-1]) if len(atr) > 0 and not pd.isna(atr.iloc[-1]) else (df['close'].iloc[-1] * 0.02)


analyzer = TechnicalAnalyzer()