import pandas as pd
import pandas_ta as ta
from binance import Client


class TaManager:
    def __init__(self, client, klines_length):
        self.client = client
        self.klines_length = self.get_interval(klines_length)

    def get_interval(self, klines_length):
        if klines_length == "1":
            return Client.KLINE_INTERVAL_1MINUTE
        elif klines_length == "5":
            return Client.KLINE_INTERVAL_5MINUTE
        elif klines_length == "15":
            return Client.KLINE_INTERVAL_15MINUTE
        elif klines_length == "30":
            return Client.KLINE_INTERVAL_30MINUTE
        elif klines_length == "1H":
            return Client.KLINE_INTERVAL_1HOUR

    def get_binance_klines(self, symbol):
        return self.client.get_klines(symbol=symbol, interval=self.klines_length)

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
        Get the last rsi on Close
        """
        df.ta.rsi(14, append=True)
        ta.rsi(df['Close'], length=rsi_length)
        value = df['RSI_14'].iloc[-1]
        return value
