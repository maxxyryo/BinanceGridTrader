from binance import Client
from binance.exceptions import BinanceAPIException
from colorama import Fore, init
import math


class BinanceTrader:
    def __init__(self, public_key, private_key):
        self.public_key = public_key
        self.private_key = private_key
        self.client = Client(api_key=self.public_key, api_secret=self.private_key)

    @staticmethod
    def float_precision(f, n):
        """
        Calculate float precisions based on exchange data
        """
        n = int(math.log10(1 / float(n)))
        f = math.floor(float(f) * 10 ** n) / 10 ** n
        f = "{:0.0{}f}".format(float(f), n)
        print(Fore.LIGHTCYAN_EX + f"{f}")
        return str(int(f)) if int(n) == 0 else f

    def get_buy_grid(self, grid_count, asset_price, step, step_size, value_per_mesh):
        """
        Calculates the grid
        :param grid_count:
        :param asset_price:
        :param step:
        :return:
        """
        levels = []
        lvl = 1
        step_value = 0
        print(Fore.LIGHTGREEN_EX + f"GRID data...")
        for x in range(grid_count):
            step_value += asset_price * step
            grid_level = asset_price - step_value
            coin_currency_quantity = float(self.float_precision(value_per_mesh / grid_level, step_size))
            lot_size = str(step_size).index('1') - 1
            if lot_size < 0:
                coin_currency_quantity = int(coin_currency_quantity)

            print(f"L{lvl} @ {grid_level:.8f} USDT SUM: {coin_currency_quantity}")
            lvl += 1
            grid_value = {"qty": coin_currency_quantity,
                          "levelPrice": grid_level}
            levels.append(grid_value)
        return levels

    def get_limit_sell_info(self, price, gain_perc, coin_quantity, tick_size, step_size):
        """
        Get the data on limit sell
        :return:
        """
        target = price * (1.00 + gain_perc)
        price = float(self.float_precision(target, tick_size))
        coin_currency_quantity = float(self.float_precision(coin_quantity, step_size))
        return price, coin_currency_quantity

    def get_tick_and_step_size(self, symbol_data):
        """
        Process symbol data
        """
        tick_size = None
        step_size = None
        for filt in symbol_data['filters']:
            if filt['filterType'] == 'PRICE_FILTER':
                tick_size = float(filt['tickSize'])
            elif filt['filterType'] == 'LOT_SIZE':
                step_size = float(filt['stepSize'])
        return tick_size, step_size

    def get_my_trades(self, symbol, order_id):
        return self.client.get_my_trades(symbol=symbol, orderId=order_id)[0]

    def get_orderbook_data(self, symbol):
        return self.client.get_orderbook_ticker(symbol=symbol)

    def get_symbol_data(self, symbol):
        return self.client.get_symbol_info(symbol=symbol)

    def get_order(self, symbol, order_id):
        return self.client.get_order(symbol=symbol, orderId=order_id)

    def make_limit_buy(self, symbol, qty_str, value):
        try:
            order = self.client.order_limit_buy(
                symbol=symbol,
                quantity=qty_str,
                price=value)
            return order
        except BinanceAPIException as e:
            return e.message

    def make_limit_sell(self, symbol, quantity, price):
        try:
            sell_order = self.client.order_limit_sell(
                symbol=symbol,
                quantity=f"{quantity}",
                price=price)
            return sell_order
        except BinanceAPIException as e:
            return e.message

    def make_oco_sell(self, symbol, quantity, price, stop_price, stop_limit_price):
        try:
            oco_order = self.client.order_oco_sell(
                symbol=symbol,
                quantity=quantity,
                price=price,
                stopPrice=stop_price,
                stopLimitPrice=stop_limit_price,
                stopLimitTimeInForce='GTC')
            return oco_order
        except BinanceAPIException as e:
            return e.message
