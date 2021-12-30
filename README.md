# Binance Multi Coin Grid Trader


## Install 

### Clone the repository
```buildoutcfg
git clone https://github.com/AnimusXCASH/BinanceGridTrader.git
```
### Install Project Requirements
```
pip3 install requirements.txt
```

### Bot Setup File
Create file into main directory under the name `botSetup.json` and fill in following requirements.

```json
{
  "binancePrivate":".....",
  "binancePublic": ".....",
  "markets": ["BNBUSDT", "MATICUSDT"],  // List of pairs to create grid
  "gridDistance": 0.005,  //Set at 0.5% distance between grids
  "grids": 4,  // Amount of grids for limit buy to be created...currently 4
  "base": "bid", // Which based to use for grid calculation: bid, ask
  "dollarPerCoin": 240, // UDST devoted per pair
  "gain": 0.020 // Exit percentage for limit sell from marked buy price
}

```

## Run the script from CMD 
```
python main.py
```
or
```
python3 main.py
```
