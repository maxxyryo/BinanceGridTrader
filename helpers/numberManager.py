class NumberManager():
    def __init__(self):
        pass

    def count_decimals(self, filter: str):
        """
        Returns the data on how many decimal places
        :param filter: String of float representing decimal places
        :return: integer to be used to determine minimal lot and decimal places
        """
        price = str(float(filter))
        dec = price[::-1].find('.')
        return dec

#
# print(NumberManager().count_decimals(0.0000001))
