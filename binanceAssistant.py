import math


class BinanceAssistant:
    def __init__(self, client):
        self.client = client

    def precision_calculations(self, f, n):
        """
        Get the float precision for trades
        """
        n = int(math.log10(1 / float(n)))
        f = math.floor(float(f) * 10 ** n) / 10 ** n
        f = "{:0.0{}f}".format(float(f), n)
        return str(int(f)) if int(n) == 0 else f

    def get_tick_and_step_size(self, symbol: str):
        tick_size = None
        step_size = None
        symbol_info = self.client.get_symbol_info(symbol)
        for filt in symbol_info['filters']:
            if filt['filterType'] == 'PRICE_FILTER':
                tick_size = float(filt['tickSize'])
            elif filt['filterType'] == 'LOT_SIZE':
                step_size = float(filt['stepSize'])
        return tick_size, step_size

    def get_buy_info(self, symbol, price):
        tick_size, step_size = self.get_tick_and_step_size(symbol)
        price = float(self.precision_calculations(price, tick_size))
        coin_currency_quantity = float(self.float_precision(self.get_balance(self.base_currency) / price, step_size))
        return price, coin_currency_quantity
