import time
import ccxt
import numpy as np
import pandas as pd
import datetime
import talib

with open("바이낸스.txt") as f:
    lines = f.readlines()
    api_key = lines[0].strip() 
    secret = lines[1].strip() 

def get_ohlcv(ticker, days):
    """ohlcv 조회"""
    ohlcv = exchange.fetch_ohlcv(ticker, timeframe='4h', limit=days)
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

def get_condition_max_price(days, condition, df):
    """전 봉의 종가 조회"""
    array = np.array(df[condition])
    price = array[:days].max()
    return price

def get_condition_min_price(days, condition, df):
    """전 봉의 종가 조회"""
    array = np.array(df[condition])
    price = array[:days].min()
    return price

def get_current_price(ticker):
    """현재가 조회"""
    orderbook = exchange.fetch_order_book(ticker)
    price = orderbook['asks'][0][0]
    return price

def get_df(ticker, days1, days2, delay = 0):
    """속도 향상을 위한 공통 df"""
    dfLong = get_ohlcv(ticker, days1 + delay)
    dfShort = dfLong[days2:]
    return dfLong, dfShort

def buy(ticker):
    """매수조건 확인 후 매수"""
    global fire, reset, profit, side

    atr = get_ATR(ticker, 14)
    amount = round(usdt * 0.01 / (2 * atr), 3)
    if amount == 0.0:
        amount = 0.001
    df = get_ohlcv(ticker, 1)
    order = False  
    re_condition = ""
    current = get_current_price(ticker)

    if exhighL < get_condition_max_price(1, 'high', df):
        # if profit[ticker] == True:
        #     profit[ticker] = False
        #     reset[ticker] = 1
        #     return
        exchange.create_market_buy_order(ticker, amount)
        print('LONG: ' + ticker)
        re_condition = 'SELL'
        order = True
        price[ticker] = current + atr
        side[ticker] = 'LONG'
    elif exlowL > get_condition_min_price(1, 'low', df):
        # if profit[ticker] == True:
        #     profit[ticker] = False
        #     reset[ticker] = 1
        #     return
        exchange.create_market_sell_order(ticker, amount)
        print('SHORT: ' + ticker)
        re_condition = 'BUY'
        order = True
        price[ticker] = current - atr
        side[ticker] = 'SHORT'

    if order == True:
        bought_list.append(ticker)
        time.sleep(1)
        stop(re_condition, ticker)
        fire[ticker] += 1
        reset[ticker] = 1

def check(ticker):
    global reset, price, side
    current = get_current_price(ticker)
    if side[ticker] != '':
        if side[ticker] == 'LONG' and current > price[ticker]:
            reset[ticker] = 0
        elif side[ticker] == 'SHORT' and current < price[ticker]:
            reset[ticker] = 0
    elif side[ticker] == '':
        reset[ticker] = 0

def stop(condition, ticker):
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/BUSD', 'BUSD'):
            ticker = str(elem['symbol']).replace('BUSD', '/BUSD')
            amount = str(elem['positionAmt']).replace('-', '')
            if condition == 'SELL':
                price = get_current_price(ticker) - 2 * get_ATR(ticker, 14)
            elif condition == 'BUY':
                price = get_current_price(ticker) + 2 * get_ATR(ticker, 14)
            exchange.create_order(ticker, 'STOP', condition, amount, price, {'stopPrice': price, 'reduceOnly':'true'})
            break

def sell(ticker):
    """매수조건 확인 후 매도"""
    global fire, reset, profit, price, side
    balance = exchange.fetch_balance()['info']['positions']
    df = get_ohlcv(ticker, 1)
    condition = ''
    info = {}

    for elem in balance:
        if ticker.replace('/BUSD', 'BUSD') == elem['symbol']:
            if  float(elem['positionAmt']) < 0:
                condition = 'SELL'
                info = elem
                break
            elif float(elem['positionAmt']) > 0:
                condition = 'BUY'
                info = elem
                break

    if info != {} and info['initialMargin'] != '0':
        ticker = str(info['symbol']).replace('BUSD', '/BUSD')
        amount = str(info['positionAmt']).replace('-', '')
        pnl = float(info['unrealizedProfit'])
        if condition != '':
            if exlowS > get_condition_min_price(1, 'low', df) and condition == 'BUY':
                # if pnl > 0:
                #     profit[ticker] = True
                exchange.create_market_sell_order(ticker, amount, {'reduceOnly':'true'})
                print('Close: ' + ticker)
                fire[ticker] = 0
                reset[ticker] = 0
                side[ticker] = ''
                price[ticker] = None
            if exhighS < get_condition_max_price(1, 'high', df) and condition == 'SELL':
                # if pnl > 0:
                #     profit[ticker] = True
                exchange.create_market_buy_order(ticker, amount, {'reduceOnly':'true'})
                print('Close: ' + ticker)
                fire[ticker] = 0
                reset[ticker] = 0
                side[ticker] = ''
                price[ticker] = None

def update_boughtlist():
    global fire, reset
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        ticker = str(elem['symbol']).replace('BUSD', '/BUSD')
        if elem['initialMargin'] == '0':
            if ticker in bought_list:
                order = exchange.fetchOpenOrders(ticker)
                bought_list.remove(ticker)
                fire[ticker] = 0
                reset[ticker] = 0
                side[ticker] = ''
                price[ticker] = None
                for elem in order:
                    exchange.cancel_order(elem['id'], ticker)

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

buy_list = ['ETH/BUSD', 'BTC/BUSD']
bought_list = []
fire = {}
price = {}
side = {}
reset = {}
profit = {}

for ticker in buy_list:
    fire[ticker] = 0
    price[ticker] = None
    side[ticker] = ""
    reset[ticker] = 0
    profit[ticker] = False

usdt = exchange.fetch_balance()['BUSD']['free']
balance = exchange.fetch_balance()['info']['positions']
for elem in balance:
    if elem['initialMargin'] != '0' and ('BUSD' in str(elem['symbol'])):
        ticker = str(elem['symbol']).replace('BUSD', '/BUSD')
        bought_list.append(ticker)

print('start')
while True:
    try:
        hour = datetime.datetime.now().hour % 4
        mininute = datetime.datetime.now().minute
        second = datetime.datetime.now().second
        print(str(mininute) + 'm ' + str(second) + 's')

        if hour == 0 and mininute == 0 and 1 <= second <= 7:
            for ticker in buy_list:
                check(ticker)

        if len(bought_list) == 0:
            usdt = exchange.fetch_balance()['BUSD']['free']

        for ticker in buy_list:
            dfl, dfs = get_df(ticker, 20, 10, 1)
            exhighL = get_condition_max_price(20,'high', dfl)
            exhighS = get_condition_max_price(10,'high', dfs)
            exlowL = get_condition_min_price(20, 'low', dfl)
            exlowS = get_condition_min_price(10, 'low', dfs)
            if ticker in bought_list:
                sell(ticker)
            if ((ticker not in bought_list) or (fire[ticker] < 3)) and reset[ticker] == 0:
                buy(ticker)

        update_boughtlist()
        print('reset: ' + str(reset))
        print('fire: ' + str(fire))
        print('price: ' + str(price))
        print('side: ' + str(side))
        print('profit: ' + str(profit))
        time.sleep(0.1)
    except Exception as e:
        print(e)