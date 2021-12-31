import pandas as pd
import pandas_ta as ta
from binance import Client


class TaManager:
    def __init__(self, client):
        self.client = client

    def get_binance_klines(self, symbol):
        return self.client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE)

    def process_klines(self, klines):
        """
        Process klines
        """
        df = pd.DataFrame(klines, dtype=float, columns=('Open Time',
                                                        'Open',
                                                        'High',
                                                        'Low',
                                                        'Close',
                                                        'Volume',
                                                        'Close time',
                                                        'Quote asset volume',
                                                        'Number of trades',
                                                        'Taker buy base asset volume',
                                                        'Taker buy quote asset volume',
                                                        'Ignore'))

        df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
        df = df.drop(df.columns[[7, 8, 9, 10, 11]], axis=1)
        df.set_index("Open Time", inplace=True)
        return df

    def get_rsi(self, df, rsi_length: int):
        """
        Get the rsi values based on close
        """
        df.ta.rsi(14, append=True)
        ta.rsi(df['Close'], length=rsi_length)
        return df
