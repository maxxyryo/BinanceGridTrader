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
klines_manager = TaManager(client=binance_trader.client, klines_length=settings["rsiTimeframe"])

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
    tick_size, step_size = binance_trader.get_tick_and_step_size(symbol_data)

    if GRID_BASE == "BID":
        base_price = data["bidPrice"]
        print(Fore.GREEN + f'Last BID is {base_price} USDT')

    elif GRID_BASE == "ASK":
        data = binance_trader.get_orderbook_data(symbol=symbol)
        base_price = data["askPrice"]
        print(Fore.GREEN + f'Last ASK is {base_price} USDT')

    print(Fore.BLUE + f'Creating {GRID_LEVELS} GRID levels with drop of {INTERVAL / (1 ** 2)}% per GRID...')

    grid_mesh = binance_trader.get_buy_grid(grid_count=GRID_LEVELS, asset_price=float(base_price), step=INTERVAL,
                                            step_size=step_size, value_per_mesh=int(DOLLAR_PER_TOKEN / GRID_LEVELS))

    print(Fore.BLUE + f'Deploying GRID to binance')
    level = 1

    for mesh_value in grid_mesh:
        qty = mesh_value["qty"]
        price_level = mesh_value["levelPrice"]
        print(Fore.CYAN + f'BL{level} @ {price_level} deployed with QTY {qty}{symbol}...')

        # Try to make an limit order order
        result = binance_trader.make_limit_buy(symbol=symbol, qty_str=qty, value=f'{price_level:.8f}')

        # Process binance result response and store it to database if successful
        if isinstance(result, dict):
            order_id = result["orderId"]
            price = result["price"]
            qty = result["origQty"]
            print(Fore.CYAN + f'Storing order details to DB...')
            if backoffice.grid_manager.store_limit_order({
                "gridL": f"L{level}",
                "orderId": order_id,
                "price": price,
                "symbol": result["symbol"],
                "origQty": qty}):
                print(Fore.YELLOW + f"Order stored successfully...")
                print(Fore.GREEN + f'Limit order deployed at L{level}')
                level += 1
            else:
                print(Fore.RED + f'Could not store order in database')
        else:
            print(Fore.RED + f'L{level} grid could not be deployed due to API error: {result}')
    print(Fore.GREEN + f'GRID for symbol {symbol} successfully deployed')


def check_grid_state(symbol):
    """
    Main program to runt the bot
    :return:
    """
    # Monitor grid status

    limit_buy_orders = backoffice.grid_manager.get_buy_limit_orders(ticker=symbol)
    limit_sell_orders = backoffice.grid_manager.get_sell_limit_orders(ticker=symbol)
    print(Fore.MAGENTA + f'GRID: {symbol}')

    # Check if previous GRID is still live
    if limit_sell_orders or limit_buy_orders:
        # TODO Modify this from here on
        open = 1
        open_sell = 1
        # Symbol data for exchange
        symbol_data = backoffice.grid_manager.get_symbol_info(symbol=symbol)
        tick_size, step_size = binance_trader.get_tick_and_step_size(symbol_data)

        # Check limit buy orders
        if limit_buy_orders:
            for x in limit_buy_orders:
                current_order = binance_trader.get_order(symbol=x["symbol"], order_id=x["orderId"])
                if current_order['status'] == 'FILLED':
                    print(Fore.GREEN + f'Order ID {x["orderId"]} has been FILLED')
                    print(Fore.YELLOW + f'Creating LIMIT SELL')
                    purchased_value_usdt = current_order["cummulativeQuoteQty"]  # Total purchase value
                    purchase_qty = float(current_order["executedQty"])  # Executed quantity

                    # Get the trade details from order
                    trade_details = binance_trader.get_my_trades(symbol=x["symbol"], order_id=x["orderId"])
                    purchase_price = trade_details["price"]  # Purchase price of the executed limit order
                    commission = trade_details["commission"]  # Commision charged for quantity
                    final_quantity = purchase_qty - float(commission)  # removing commission from the purchase qty

                    grid_level_price, coin_quantity = binance_trader.get_limit_sell_info(price=purchase_price,
                                                                                         gain_perc=GAIN,
                                                                                         coin_quantity=final_quantity,
                                                                                         tick_size=tick_size,
                                                                                         step_size=step_size)
                    # Place limit sell order
                    print(
                        Fore.YELLOW + f'Creating sell limit order of buy order {current_order["orderId"]} at {x["gridL"]}....')

                    # TODO rewrite this for OCO
                    sell_result = binance_trader.make_limit_sell(symbol=symbol,
                                                                 quantity=f"{coin_quantity}",
                                                                 price=grid_level_price)
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
            print(Fore.LIGHTRED_EX + f'{symbol} has no limit buys marked in DB')

        # Check limit sell order statuses
        if limit_sell_orders:
            for y in limit_sell_orders:
                current_sell_limit_order = binance_trader.get_order(symbol=y["symbol"], order_id=y["orderId"])
                if current_sell_limit_order['status'] == 'FILLED':
                    print(Fore.GREEN + f"GRID: {y['gridL']} TRADE COMPLETED")
                    # TODO Integrate other data from the past to be stored for history
                    # Store the sell order in DB
                    if backoffice.grid_manager.store_to_done(current_sell_limit_order):
                        print(Fore.GREEN + "Details stored successfully to database ")
                        if backoffice.grid_manager.remove_sell_limit_order(y["orderId"]):
                            print(Fore.GREEN + 'Sell limit order removed after moving to successful')
                        else:
                            print(Fore.RED + "Could not remove from limit sell collection")

                    else:
                        print(Fore.RED + "Could not store to done collection")
                else:
                    print(Fore.LIGHTRED_EX + f'GL{open_sell}: Order with ID {y["orderId"]} still open')
                    open_sell += 1
        else:
            print(Fore.LIGHTRED_EX + f'{symbol} has no limit sells marked in DB')

    # If no levels deployed initiate a new grid if market manager allows it
    if len(limit_buy_orders) + len(limit_sell_orders) == 0:
        print(Fore.RED + f'NO Grid deployed for symbol {symbol} anymore')
        print(Fore.RED + f'Checking market manager')
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
    """
    Check the grids on the script start. If no grids active, it will create fresh grid for symbol
    """
    # Check if not active orders and initiate the grid
    print('Check symbols on run...')
    for s in symbols:
        if not backoffice.grid_manager.get_buy_limit_orders(s):
            if not backoffice.grid_manager.get_sell_limit_orders(s):
                print(Fore.LIGHTGREEN_EX + f'No active GRID for {s} found....Initiating @  {datetime.utcnow()}')
                print(Fore.LIGHTGREEN_EX + f'Checking RSI level of {settings["rsiTimeframe"]} minute candle')
                # Check rsi values
                ohlcv = klines_manager.get_binance_klines(symbol=s)
                ohlcv = klines_manager.process_klines(klines=ohlcv)
                rsi = klines_manager.get_rsi(df=ohlcv, rsi_length=14)
                if rsi < settings["rsiManager"]:
                    print(Fore.LIGHTGREEN_EX + f'RSI = {rsi} < than limit {settings["rsiManager"]}...deploying')
                    deploy_grid(symbol=s)
                else:
                    print(
                        Fore.RED + f"Could not deploy GRID for symbol {s} as the 5 minutes RSI is greater than {settings['rsiManager']} = {rsi}")
        else:
            pass
    return


def check_symbols_db():
    for s in SYMBOLS:
        if not backoffice.grid_manager.check_symbol_data(symbol=s):
            # Get symbol data from exchange
            symbol_data = binance_trader.get_symbol_data(symbol=s)
            if backoffice.grid_manager.store_symbol_data(data=symbol_data):
                pass
            else:
                pass
        else:
            pass
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
