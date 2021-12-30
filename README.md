# Binance Multi Coin Grid Trader

## About

- [x] Create limit buy order grid for specific market under set conditions (Grid level distance, grid count,etc.) equally distributed.
  - [x] Grids are created on bot startup if no previous grids in database founds
- [x] Monitors grid orders and once purchase is done, it automatically sets the sell limits based on setup parameters
- [x] Monitors limit sell orders 
- [x] Activities stored in Mongo Database collections for tracking
  - [x] Limit buy order grids
  - [x] limit sell orders
  - [x] completed grids
  - [ ] performance calculation
- [ ] Once Grids are completed make new grids once grid is completed
- [ ] Overall account performance tracking

## Install  

### Clone the repository
```buildoutcfg
git clone https://github.com/AnimusXCASH/BinanceGridTrader.git
```
### Install Project Requirements
```
pip3 install -r requirements.txt
```

### Install MongoDB

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
  "monitor": 120 //Seconds between grid re-checks currently set to 120
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
