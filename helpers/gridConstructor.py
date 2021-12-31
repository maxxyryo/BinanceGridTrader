from colorama import init, Fore

init(autoreset=True)


class GridConstructor:
    def __init__(self):
        pass

    def get_buy_grid(self, grid_count, asset_price, step, price_filter_decimal: int):
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

    def get_sell_grid_single(self, buy_price, gain, decimal_places):
        """
        Grid construction
        """
        return (int(buy_price * (1.00 + gain) * (10 ** decimal_places))) / (10 ** decimal_places)
