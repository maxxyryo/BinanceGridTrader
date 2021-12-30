class GridManager:
    """Class dealing with the Layer two wallets"""

    def __init__(self, connection):
        """Connection to Database and Crypto Link collections"""
        self.connection = connection
        self.grid_trader = self.connection['GridTrader']
        self.coin_grids = self.grid_trader.grids
        self.limit_buy = self.grid_trader.limitBuy
        self.limit_sell = self.grid_trader.limitSell
        self.done = self.grid_trader.done
        self.symbol_data = self.grid_trader.symbolInfo

    def check_symbol_data(self, symbol):
        result = self.symbol_data.find_one({"symbol":symbol})
        if result:
            return True
        else:
            return False

    def get_symbol_info(self, symbol:str):
        return self.symbol_data.find_one({"symbol":symbol})

    def store_symbol_data(self, data):
        result = self.symbol_data.insert_one(data)
        return result.inserted_id

    def store_limit_order(self, data):
        result = self.limit_buy.insert_one(data)
        return result.inserted_id

    def store_sell_limit_order(self, data):
        result = self.limit_sell.insert_one(data)
        return result.inserted_id

    def get_buy_limit_orders(self, ticker):
        result = list(self.limit_buy.find({"symbol": ticker},
                                          {"_id": 0}))
        return result

    def get_sell_limit_orders(self, ticker):
        result = list(self.limit_sell.find({"symbol": ticker},
                                           {"_id": 0}))
        return result

    def remove_buy_limit_order(self,order_id):
        result = self.limit_buy.delete_one({"orderId":order_id})
        return result.deleted_count == 1


    def store_to_done(self, data):
        result = self.done.insert_one(data)
        return result.inserted_id