from binance import Client
from datetime import datetime
from colorama import Fore, init
import time
from pprint import pprint
from backend.backendManager import BackOffice
from helpers.fileManagement import FileManager
from helpers.numberManager import NumberManager
from helpers.klinesManager import TaManager
from helpers.gridConstructor import GridConstructor
from helpers.binaceTrader import BinanceTrader

init(autoreset=True)
file_manager = FileManager()
grid_constructor = GridConstructor()
backoffice = BackOffice()
number_manager = NumberManager()
settings = file_manager.read_json_file(file_name=f'botSetup.json')
binance_trader = BinanceTrader(public_key=settings["binancePublic"], private_key=settings["binancePrivate"])
klines_manager = TaManager(binance_trader.client)

# Loading grid data
SYMBOLS = settings["markets"]
INTERVAL = settings["gridDistance"]
GRID_LEVELS = settings["grids"]
GRID_BASE = settings["base"].upper()

# Money Management
DOLLAR_PER_TOKEN = settings["dollarPerCoin"]
GAIN = settings["gain"]


def deploy_grid(symbol):
    """
    Deploys the greed and created limit buy orders
    :return:
    """
    print(Fore.CYAN + f'Initializing GRID for {symbol} based on {GRID_BASE} as a base (L0)...')
    # Getting base and calcuating GRID
    data = binance_trader.get_orderbook_data(symbol=symbol)

    # Get symbol details for processing
    symbol_data = backoffice.grid_manager.get_symbol_info(symbol=symbol)

    price_filter = [x for x in symbol_data["filters"] if x["filterType"] == 'PRICE_FILTER'][0]
    lot_size = [x for x in symbol_data["filters"] if x["filterType"] == 'LOT_SIZE'][0]

    # get exchange price characteristics
    minimum_price_decimal = number_manager.count_decimals(price_filter["minPrice"])
    minimum_lot_size_decimal = number_manager.count_decimals(lot_size["minQty"])

    if GRID_BASE == "BID":
        base_price = data["bidPrice"]
        print(Fore.GREEN + f'Last BID is {base_price} USDT')

    elif GRID_BASE == "ASK":
        data = binance_trader.get_orderbook_data(symbol=symbol)
        base_price = data["askPrice"]
        print(Fore.GREEN + f'Last ASK is {base_price} USDT')

    print(Fore.BLUE + f'Creating {GRID_LEVELS} GRID levels with drop of {INTERVAL * (1 ** 2)}% per GRID...')
    buy_grid = grid_constructor.get_buy_grid(grid_count=GRID_LEVELS, asset_price=float(base_price), step=INTERVAL,
                                             price_filter_decimal=minimum_price_decimal)
    print(buy_grid)

    level = 1
    dollar_size = int(DOLLAR_PER_TOKEN / GRID_LEVELS)  # Equal distribution of dollars across range
    print(Fore.CYAN + f'Making Limit orders based on GRID data with {dollar_size} per GRID ')

    grid_quantities_status = True  # Check if GRID quantities fit instructions of exchange
    for qty in buy_grid:
        if not qty > float(lot_size["minQty"]):
            grid_quantities_status = False

    if grid_quantities_status:
        # Make BUY LIMIT ORDERS to Binance
        for value in buy_grid:
            qty = (dollar_size / value)
            qty = int(qty * (10 ** minimum_lot_size_decimal))
            qty = qty / (10 ** minimum_lot_size_decimal)
            qty_str = "{:0.0{}f}".format(qty, 3)
            print(f"{symbol}: {dollar_size} (QTY: {qty_str}) @ {value}")

            # Try to make an order
            result = binance_trader.make_limit_buy(symbol=symbol, qty_str=qty_str, value=value)
            # Process result
            if isinstance(result, dict):
                order_id = result["orderId"]
                price = result["price"]
                qty = result["origQty"]
                print(f'{order_id} @ {price} with QTY {qty}')

                # TODO integrate total money spent
                if backoffice.grid_manager.store_limit_order({
                    "gridL": f"L{level}",
                    "orderId": order_id,
                    "price": price,
                    "symbol": result["symbol"],
                    "origQty": qty}):
                    print(Fore.YELLOW + f"Order stored successfully")
                    print(Fore.GREEN + f'Limit order deployed at L{level}')
                    level += 1
                else:
                    print(Fore.RED + f'Could not store order in database')
            else:
                print(Fore.RED + f'L{level} grid could not be deployed due to API error: {result}')
        print(Fore.GREEN + f'GRID for symbol {symbol} successfully deployed')
    else:
        print(Fore.RED + f"GRID could not be created as monomum quantity demands are not met or symbol. "
                         f"Please increase the MONEY used or decrease the amount of grids")


def check_grid_state(symbol):
    """
    Main program to runt the bot
    :return:
    """
    # Monitor grid status

    limit_buy_orders = backoffice.grid_manager.get_buy_limit_orders(ticker=symbol)
    print(Fore.MAGENTA + f'GRID: {symbol}')
    print(Fore.WHITE + f'Total registered buy limit orders in DB {len(limit_buy_orders)}')
    open = 1

    # Symbol data for exchange
    symbol_data = backoffice.grid_manager.get_symbol_info(symbol=symbol)
    price_filter = [x for x in symbol_data["filters"] if x["filterType"] == 'PRICE_FILTER'][0]
    lot_size = [x for x in symbol_data["filters"] if x["filterType"] == 'LOT_SIZE'][0]
    minimum_price_decimal = number_manager.count_decimals(price_filter["minPrice"])
    minimum_lot_size_decimal = number_manager.count_decimals(lot_size["minQty"])

    if limit_buy_orders:
        for x in limit_buy_orders:
            current_order = binance_trader.get_order(symbol=x["symbol"], order_id=x["orderId"])
            if current_order['status'] == 'FILLED':
                print(Fore.GREEN + f'Order ID {x["orderId"]} has been FILLED')
                print(Fore.YELLOW + f'Creating LIMIT SELL')
                purchased_value_usdt = current_order["cummulativeQuoteQty"]  # Total purchase value
                purchase_qty = float(current_order["executedQty"])  # Executed quantity

                # Get the trade details from order
                trade_details = binance_trader.get_my_trades(symbol=x["symbol"])
                commission = trade_details["commission"]  # Commision charged
                purchase_price = trade_details["price"]  # Purchase price of the executed limit order

                # Calculate selling quantity
                final_amount = purchase_qty - float(commission)  # removing commission from the purchase qty
                atomic = int(final_amount * (10 ** minimum_lot_size_decimal))
                final_normal = atomic / (10 ** minimum_lot_size_decimal)
                price = grid_constructor.get_sell_grid_single(buy_price=float(purchase_price), gain=GAIN,
                                                              decimal_places=minimum_price_decimal)  # Get the targeted price for sell

                # Place limit sell order
                print(
                    Fore.YELLOW + f'Creating sell limit order of buy order {current_order["orderId"]} at {x["gridL"]}....')

                # TODO rewrite this for OCO
                sell_result = binance_trader.make_limit_sell(symbol=symbol,
                                                             quantity=f"{final_normal}",
                                                             price=price)
                if isinstance(sell_result, dict):
                    # Remove from limit buys db
                    if backoffice.grid_manager.remove_buy_limit_order(order_id=current_order["orderId"]):
                        # Add to limit sells new order
                        if backoffice.grid_manager.store_sell_limit_order(data={
                            "orderId": sell_result["orderId"],
                            "price": sell_result["price"],
                            "symbol": sell_result["symbol"],
                            "origQty": sell_result["origQty"],
                            "gridL": x["gridL"]
                        }):
                            print(
                                f'New limit sell created @ {x["gridL"]} price {sell_result["price"]} '
                                f'qty {sell_result["origQty"]}{sell_result["symbol"]}')
                        else:
                            print(
                                Fore.RED + F'Could not insert SELL LIMIT TO DB: sell order ID: {sell_result["orderId"]}')
                    else:
                        print(Fore.RED + F'Could not remove BUY LIMIT FROM DB: orderID: {current_order["orderId"]}')

                elif isinstance(sell_result, str):
                    print(Fore.RED + f'{x["gridL"]} grid could not be deployed due to API error: {sell_result}')

            else:
                print(Fore.LIGHTGREEN_EX + f'{x["gridL"]}: Order with ID {x["orderId"]} still open')
                open += 1
    else:
        print(Fore.RED + f'{symbol} has no limit buys marked in DB')

    # Check limit sell order statuses
    open_sell = 1
    limit_sell_orders = backoffice.grid_manager.get_sell_limit_orders(ticker=symbol)
    if limit_sell_orders:
        print(Fore.WHITE + f'Total registered sell limit orders in DB {len(limit_sell_orders)}')
        for y in limit_sell_orders:
            current_sell_limit_order = binance_trader.get_order(symbol=y["symbol"], order_id=y["orderId"])
            if current_sell_limit_order['status'] == 'FILLED':
                print(Fore.GREEN + f"GRID: {y['gridL']} TRADE COMPLETED")
                # TODO Integrate other data from the past to be stored for history
                # Store the sell order in DB
                if backoffice.grid_manager.store_to_done(current_sell_limit_order):
                    print(Fore.GREEN + "Details stored successfully to database ")
                    if backoffice.grid_manager.remove_sell_limit_order(y["orderId"]):
                        print(Fore.GREEN + 'Sell limit order removed after moving to successfull')
                    else:
                        print(Fore.RED + "Could not remove from limit sell collection")

                else:
                    print(Fore.RED + "Could not store to done collection")
            else:
                print(Fore.LIGHTRED_EX + f'GL{open_sell}: Order with ID {y["orderId"]} still open')
                open_sell += 1
    else:
        print(Fore.RED + f'{symbol} has no limit sells marked in DB')

    if len(limit_buy_orders) + len(limit_sell_orders) == 0:
        print(Fore.RED + f'NO Grid deployed for symbol {symbol}')
        ohlcv = klines_manager.get_binance_klines(symbol=symbol)
        ohlcv = klines_manager.process_klines(klines=ohlcv)
        rsi = klines_manager.get_rsi(df=ohlcv, rsi_length=14)

        if rsi < settings["rsiManager"]:
            print(Fore.LIGHTGREEN_EX + f'RSI less then limit {settings["rsiManager"]}...deploying new grid')
            deploy_grid(symbol=symbol)
        else:
            print(
                Fore.RED + f"Could not deploy GRID for symbol {symbol} as the 15 minutes RSI is greater than {settings['rsiManager']}")
    else:
        pass

    print(Fore.CYAN + f"Done checking symbol {symbol}\n" \
                      "==============================================")
    return


def check_symbol_grids(symbols):
    # Check if not active orders and initiate the grid
    print('Check symbols on run...')
    for s in symbols:
        if not backoffice.grid_manager.get_buy_limit_orders(s):
            if not backoffice.grid_manager.get_sell_limit_orders(s):
                print(Fore.LIGHTGREEN_EX + f'No active GRID for {s} found....Initiating @  {datetime.utcnow()}')
                print(Fore.LIGHTGREEN_EX + f'Checking RSI level of 15 minute candle')
                # Check rsi values
                ohlcv = klines_manager.get_binance_klines(symbol=s)
                ohlcv = klines_manager.process_klines(klines=ohlcv)
                rsi = klines_manager.get_rsi(df=ohlcv, rsi_length=14)

                if rsi < settings["rsiManager"]:
                    print(Fore.LIGHTGREEN_EX + f'RSI < than limit {settings["rsiManager"]}...deploying')
                    deploy_grid(symbol=s)
                else:
                    print(
                        Fore.RED + f"Could not deploy GRID for symbol {s} as the 15 minutes RSI is greater than {settings['rsiManager']}")
        else:
            pass
    return


def check_symbols_db():
    print("Checking symbol details on start")
    for s in SYMBOLS:
        if not backoffice.grid_manager.check_symbol_data(symbol=s):
            # Get symbol data from exchange
            symbol_data = binance_trader.get_symbol_data(symbol=s)
            if backoffice.grid_manager.store_symbol_data(data=symbol_data):
                print(f'{s} data has been stored into database successfully')
            else:
                print(f'Could not store {s} data from exchange')
        else:
            print(f'{s} details are already stored in database')
    return


def main():
    print("Live symbols:")
    for x in SYMBOLS:
        print(x)
    print("================")

    check_symbols_db()  # Check if symbol data for trading is store in DB to pull the data out
    check_symbol_grids(SYMBOLS)
    print(Fore.GREEN + f'All symbols have been checked and deployed')
    print(Fore.LIGHTGREEN_EX + f'Initiating grid monitor...')
    print(Fore.CYAN + '-----------------------\n'
                      'Monitoring GRIDS...\n'
                      '-----------------------')
    while True:
        print(Fore.CYAN + f'Checking grid status @ {datetime.utcnow()}')
        for s in SYMBOLS:
            check_grid_state(s)
        print(f'All GRIDS checked going to sleep for 120 seconds')
        time.sleep(settings["monitor"])


if __name__ == '__main__':
    main()

"""
TODO:
- Store grid start to file and mark down grids
- Integrate RSI to create new grids based on RSI
- Monitor GRID HITS of one level
- Determine when to create new grid "GAP" according to first GRID
"""
