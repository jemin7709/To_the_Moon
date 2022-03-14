import time
import ccxt
import numpy as np
import pandas as pd
import talib
from pprint import pprint

with open("바이낸스.txt") as f:
    lines = f.readlines()
    api_key = lines[0].strip() 
    secret = lines[1].strip() 

def get_ohlcv(ticker, days):
    """ohlcv 조회"""
    ohlcv = exchange.fetch_ohlcv(ticker, timeframe='1h', limit=days)
    df = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df.set_index('datetime', inplace=True)
    return df

def get_ATR(ticker, days):
    df = get_ohlcv(ticker, days * days)
    close = np.array(df['close'])
    high = np.array(df['high'])
    low = np.array(df['low'])
    ATR = talib. ATR(high, low, close, timeperiod=days)[-1]
    return round(ATR, 4)

def get_donchian_band(ticker, days, delay = 0):
    """돈키안 채널(최대, 최소) 조회"""
    df = get_ohlcv(ticker, days + delay)
    upper = np.array(df['high'])[:days].max()
    lower = np.array(df['low'])[:days].min()
    return upper, lower
    
def get_current_price(ticker):
    """현재가 조회"""
    orderbook = exchange.fetch_order_book(ticker)
    price = orderbook['asks'][0][0]
    return price

def profit_check(ticker):
    if setting_list[ticker].profit == True:
        setting_list[ticker].profit = False
        return True
    return False

def buy(ticker):
    """매수조건 확인 후 매수"""
    atr = get_ATR(ticker, 14)
    amount = round(money * 0.01 / (2 * atr), 3) if setting_list[ticker].unit == 0 else setting_list[ticker].unit
    order = False
    stop_condition = ""
    
    current = get_current_price(ticker)
    upper20, lower20 = get_donchian_band(ticker, 20, 1)
    high, low = get_donchian_band(ticker, 1)
    
    if upper20 < high: # when current high is higher than 20-day high
        if profit_check(ticker) and rest == True:
            return
        exchange.create_market_buy_order(ticker, amount)
        order = True
        setting_list[ticker].price = current + atr
        setting_list[ticker].side = 'LONG'
        stop_condition = 'SELL'
        print('LONG: ' + ticker)
    elif lower20 > low: # when current low is lower than 20-day low
        if profit_check(ticker) and rest == True:
            return
        exchange.create_market_sell_order(ticker, amount)
        order = True
        setting_list[ticker].price = current - atr
        setting_list[ticker].side = 'SHORT'
        stop_condition = 'BUY'
        print('SHORT: ' + ticker)

    if order == True:
        bought_list.append(ticker)
        setting_list[ticker].add += 1
        setting_list[ticker].unit = amount
        setting_list[ticker].check = True
        time.sleep(0.5)
        stop(stop_condition, ticker)

def stop(condition, ticker):
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/' + money_type, money_type): # ex) BTC/USDT -> BTCUSDT
            amount = str(elem['positionAmt']).replace('-', '')
            current = get_current_price(ticker)
            atr = get_ATR(ticker, 14)
            if condition == 'SELL':
                price = current - 2 * atr
            elif condition == 'BUY':
                price = current + 2 * atr
            exchange.create_order(ticker, 'STOP', condition, amount, price, {'stopPrice': price, 'reduceOnly':'true'})
            break

def sell(ticker):
    """매수조건 확인 후 매도"""
    balance = exchange.fetch_balance()['info']['positions']
    condition = ''
    info = {}

    for elem in balance:
        if ticker.replace('/' + money_type, money_type) == elem['symbol']:
            if float(elem['positionAmt']) > 0: # long
                condition = 'BUY'
                info = elem
                break
            elif  float(elem['positionAmt']) < 0: # short
                condition = 'SELL'
                info = elem
                break

    if info != {} and info['initialMargin'] != '0':
        ticker = str(info['symbol']).replace(money_type, '/' + money_type) # ex) BTCUSDT -> BTC/USDT
        amount = str(info['positionAmt']).replace('-', '')
        
        upper10, lower10 = get_donchian_band(ticker, 10, 1)
        high, low = get_donchian_band(ticker, 1)
        
        sell = False
        if condition != '':
            if condition == 'BUY' and lower10 > low: # when condition is long and current low is lower than 10-day low
                exchange.create_market_sell_order(ticker, amount, {'reduceOnly':'true'})
                sell = True
                print('Close: ' + ticker)
            elif condition == 'SELL' and upper10 < high: # when condition is short and current high is higher than 10-day high
                exchange.create_market_buy_order(ticker, amount, {'reduceOnly':'true'})
                sell = True
                print('Close: ' + ticker)
            
            time.sleep(0.5)
            
            if sell == True:
                fetchTrades = exchange.fetch_my_trades('ETH/USDT')
                pnl = float(fetchTrades[-1]['info']['realizedPnl'])
                
                if pnl != 0 and pnl > 0:
                    setting_list[ticker].profit = True
                else:
                    setting_list[ticker].profit = False
                setting_list[ticker].price = 0
                setting_list[ticker].side = ''
                setting_list[ticker].add = 0
                setting_list[ticker].unit = 0
                setting_list[ticker].check = False
                
                update_boughtlist()
                
def update_boughtlist():
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        ticker = str(elem['symbol']).replace(money_type, '/' + money_type)
        if ticker in bought_list:
            if elem['initialMargin'] == '0':
                setting_list[ticker].profit = False
                setting_list[ticker].price = 0
                setting_list[ticker].side = ''
                setting_list[ticker].add = 0
                setting_list[ticker].unit = 0
                setting_list[ticker].check = False
                bought_list.remove(ticker)
                order = exchange.fetchOpenOrders(ticker)
                for elem in order:
                    exchange.cancel_order(elem['id'], ticker)
                print('update: ', ticker)

def check(ticker):
    current = get_current_price(ticker)
    if setting_list[ticker].check == True:
        if setting_list[ticker].side == 'LONG' and current > setting_list[ticker].price:
            setting_list[ticker].check == False
        elif setting_list[ticker].side == 'SHORT' and current < setting_list[ticker].price:
            setting_list[ticker].check == False

class coin():
    def __init__(self, ticker):# -> None
        self.ticker = ticker
        self.profit = False
        self.price  = 0
        self.side   = ''
        self.add    = 0
        self.unit   = 0
        self.check  = False

exchange = ccxt.binance(config={
    'apiKey': api_key,
    'secret': secret,
    'enableRateLimit': True, # required https://github.com/ccxt/ccxt/wiki/Manual#rate-limit
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True,
        'enableRateLimit': True
    }
})

buy_list = ['BTC/USDT', 'ETH/USDT']
bought_list = []
setting_list = {}

money_type = 'USDT'
money = exchange.fetch_balance()[money_type]['total'] * 10 / len(buy_list)
balance = exchange.fetch_balance()['info']['positions']
time_check = get_ohlcv('BTC/USDT', 1).index[-1]
pyramiding = 0
rest = False

for ticker in buy_list:
    setting_list[ticker] = coin(ticker)

for elem in balance:
    if elem['initialMargin'] != '0' and (money_type in str(elem['symbol'])):
        ticker = str(elem['symbol']).replace(money_type, '/'+money_type)
        bought_list.append(ticker)
        setting_list[ticker].add += 1
 
while True:
    try:
        current_time = get_ohlcv('BTC/USDT', 1).index[-1]
        if time_check < current_time:
            time_check = current_time
            print(time_check)
            for ticker in buy_list:
                check(ticker)

        if len(bought_list) == 0:
            usdt = exchange.fetch_balance()[money_type]['free'] * 10 / len(buy_list)

        for ticker in buy_list:
            if ticker in bought_list:
                sell(ticker)
            if ((ticker not in bought_list) or (setting_list[ticker].add <= pyramiding)) and setting_list[ticker].check == False:
                buy(ticker)

        update_boughtlist()
        # for ticker in setting_list:
        #     print('ticker: {}'.format(setting_list[ticker].ticker))
        #     print('add: {}'.format(setting_list[ticker].add))
        #     print('price: {}'.format(setting_list[ticker].price))
        #     print('side: {}'.format(setting_list[ticker].side))
        #     print('profit: {}'.format(setting_list[ticker].profit))
        time.sleep(0.5)
    except Exception as e:
        print(e)

#시간측정용 코드 
start = time.time()
print("time :", time.time() - start)