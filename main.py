from binance import Client
from datetime import datetime
from colorama import Fore, init
import sys
import os
import time
from pprint import pprint
from backend.backendManager import BackOffice
from helpers.fileManagement import FileManager


init(autoreset=True)
file_manager = FileManager()
backoffice = BackOffice()

settings = file_manager.read_json_file(file_name=f'botSetup.json')

# Loading grid data
SYMBOLS = settings["markets"]
INTERVAL = settings["gridDistance"]
GRID_LEVELS =settings["grids"]
GRID_BASE = settings["base"].upper()

# Money Management
DOLLAR_PER_TOKEN = settings["dollarPerCoin"]
GAIN = settings["gain"]


client = Client(api_key=settings["binancePublic"], api_secret=settings["binancePrivate"])


def count_decimals(filter: str):
    """
    Returns the data on how many decimal places
    :param filter: String of float representing decimal places
    :return: integer to be used to determine minimal lot and decimal places
    """
    price = str(float(filter))
    return price[::-1].find('.')


def get_buy_grid(grid_count, asset_price, step, price_filter_decimal: int):
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
        to_atomic = grid_level * (10 ** 7)
        grid_level = round(to_atomic / (10 ** 7), price_filter_decimal)
        print(f"L{lvl} @ {grid_level} USDT with drop {round(step_value, price_filter_decimal)} USDT")
        lvl += 1
        levels.append(grid_level)
    return levels


def get_sell_grid_single(buy_price, decimal_places):
    return (int(buy_price * (1.00 + GAIN) * (10 ** decimal_places))) / (10 ** decimal_places)


def deploy_grid(symbol):
    """
    Deploys the greed and created limit buy orders
    :return:
    """
    print(Fore.CYAN + f'Initializing GRID for {symbol} based on {GRID_BASE} as a base (L0)...')

    # Getting base and calcuating GRID
    data = client.get_orderbook_ticker(symbol=symbol)

    # Get symbol details for processing
    symbol_data = backoffice.grid_manager.get_symbol_info(symbol=symbol)

    price_filter = [x for x in symbol_data["filters"] if x["filterType"] == 'PRICE_FILTER'][0]
    lot_size = [x for x in symbol_data["filters"] if x["filterType"] == 'LOT_SIZE'][0]

    # get exchange price characteristics
    minimum_price_decimal = count_decimals(price_filter["minPrice"])
    minimum_lot_size_decimal = count_decimals(lot_size["minQty"])

    if GRID_BASE == "BID":
        base_price = data["bidPrice"]
        print(Fore.GREEN + f'Last BID is {base_price} USDT')

    elif GRID_BASE == "ASK":
        data = client.get_orderbook_ticker(symbol=symbol)
        base_price = data["askPrice"]
        print(Fore.GREEN + f'Last ASK is {base_price} USDT')

    print(Fore.BLUE + f'Creating {GRID_LEVELS} GRID levels with drop of {INTERVAL * (1 ** 2)}% per GRID...')
    buy_grid = get_buy_grid(grid_count=GRID_LEVELS, asset_price=float(base_price), step=INTERVAL,
                            price_filter_decimal=minimum_price_decimal)

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
            order = client.order_limit_buy(
                symbol=symbol,
                quantity=qty_str,
                price=value)
            order_id = order["orderId"]
            price = order["price"]
            qty = order["origQty"]
            print(f'{order_id} @ {price} with QTY {qty}')
            if backoffice.grid_manager.store_limit_order({
                "gridL": f"L{level}",
                "orderId": order_id,
                "price": price,
                "symbol": order["symbol"],
                "origQty": qty}):
                print(Fore.YELLOW + f"Order stored successfully")
                print(Fore.GREEN + f'Limit order deployed at L{level}')
                level += 1
            else:
                print(Fore.RED + f'Could not process order')
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
    minimum_price_decimal = count_decimals(price_filter["minPrice"])
    minimum_lot_size_decimal = count_decimals(lot_size["minQty"])

    if limit_buy_orders:
        for x in limit_buy_orders:
            current_order = client.get_order(symbol=x["symbol"], orderId=x["orderId"])
            if current_order['status'] == 'FILLED':
                print(Fore.GREEN + f'Order ID {x["orderId"]} has been FILLED')
                print(Fore.YELLOW + f'Creating LIMIT SELL')
                purchased_value_usdt = current_order["cummulativeQuoteQty"]  # Total purchase value
                purchase_qty = float(current_order["executedQty"])  # Executed quantity

                # Get the trade details from order
                trade_details = client.get_my_trades(symbol=symbol, orderId=current_order["orderId"])[0]
                commission = trade_details["commission"]  # Commision charged
                purchase_price = trade_details["price"]  # Purchase price of the executed limit order

                # Calculate selling quantity
                final_amount = purchase_qty - float(commission)  # removing commission from the purchase qty
                atomic = int(final_amount * (10 ** minimum_lot_size_decimal))
                final_normal = atomic / (10 ** minimum_lot_size_decimal)
                price = get_sell_grid_single(buy_price=float(purchase_price),
                                             decimal_places=minimum_price_decimal)  # Get the targeted price for sell

                # Place limit sell order
                print(
                    Fore.YELLOW + f'Creating sell limit order of buy order {current_order["orderId"]} at {x["gridL"]}....')
                try:
                    sell_order = client.order_limit_sell(
                        symbol=symbol,
                        quantity=f"{final_normal}",
                        price=price)
                    # pprint(sell_order)

                    # Remove from limit buys db
                    if backoffice.grid_manager.remove_buy_limit_order(order_id=current_order["orderId"]):
                        # Add to limit sells new order
                        if backoffice.grid_manager.store_sell_limit_order(data={
                            "orderId": sell_order["orderId"],
                            "price": sell_order["price"],
                            "symbol": sell_order["symbol"],
                            "origQty": sell_order["origQty"],
                            "gridL": x["gridL"]
                        }):
                            print(
                                f'New limit sell created @ {x["gridL"]} price {sell_order["price"]} '
                                f'qty {sell_order["origQty"]}{sell_order["symbol"]}')
                        else:
                            print(
                                Fore.RED + F'Could not insert SELL LIMIT TO DB: sell order ID: {sell_order["orderId"]}')
                    else:
                        print(Fore.RED + F'Could not remove BUY LIMIT FROM DB: orderID: {current_order["orderId"]}')

                    # Transfer to limit sells

                except Exception as e:
                    print(Fore.RED + f"{e}")
            else:
                print(Fore.GREEN + f'{x["gridL"]}: Order with ID {x["orderId"]} still open')
                open += 1
    else:
        print(Fore.RED + f'{symbol} has no limit buys marked in DB')
    # Check limit sell order statuses
    open_sell = 1
    limit_sell_orders = backoffice.grid_manager.get_sell_limit_orders(ticker=symbol)
    if limit_sell_orders:
        print(Fore.WHITE + f'Total registered sell limit orders in DB {len(limit_sell_orders)}')
        for y in limit_sell_orders:
            current_sell_limit_order = client.get_order(symbol=y["symbol"], orderId=y["orderId"])
            if current_sell_limit_order['status'] == 'FILLED':
                print(Fore.GREEN + f"GRID: {y['gridL']} TRADE COMPLETED")
                # TODO Integrate other data from the past to be stored for history
                # Store the sell order in DB
                if backoffice.grid_manager.store_to_done(current_sell_limit_order):
                    print(Fore.GREEN + "Details stored successfully to database ")
                else:
                    print(Fore.RED + "Could ont store to database")
            else:
                print(Fore.LIGHTGREEN_EX + f'GL{open_sell}: Order with ID {y["orderId"]} still open')
                open += 1
    else:
        print(Fore.RED + f'{symbol} has no limit sells marked in DB')
    print(Fore.CYAN + f"Done checking symbol {symbol}\n" \
                      "==============================================")
    return


def check_symbol_grids(symbols):
    # Check if not active orders and initiate the grid
    print('Check symbols on run...')
    for s in symbols:
        if not backoffice.grid_manager.get_buy_limit_orders(s):
            print(Fore.LIGHTGREEN_EX + f'No active GRID for {s} found....Initiating @  {datetime.utcnow()}')
            deploy_grid(symbol=s)
        else:
            pass
    return


def check_symbols_db():
    print("Checking symbol details on start")
    for s in SYMBOLS:
        if not backoffice.grid_manager.check_symbol_data(symbol=s):
            # Get symbol data from exchange
            symbol_data = client.get_symbol_info(symbol=s)
            pprint(symbol_data)
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

    check_symbols_db()
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
