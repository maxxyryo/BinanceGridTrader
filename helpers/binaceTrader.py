from binance import Client
from binance.exceptions import BinanceAPIException


class BinanceTrader:
    def __init__(self, public_key, private_key):
        self.public_key = public_key
        self.private_key = private_key
        self.client = Client(api_key=self.public_key, api_secret=self.private_key)

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
