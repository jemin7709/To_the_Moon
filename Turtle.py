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

def get_condition_max_price(ticker, days, condition, df):
    """전 봉의 종가 조회"""
    price = df[condition][:days].max()
    return price

def get_condition_min_price(ticker, days, condition, df):
    """전 봉의 종가 조회"""
    price = df[condition][:days].min()
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

def sell_all():
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        ticker = str(elem['symbol']).replace('USDT', '/USDT')
        amount = str(elem['positionAmt']).replace('-', '')
        if float(elem['positionAmt']) > 0:
            if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
                exchange.create_market_sell_order(ticker, amount, {'reduceOnly':'true'})
                print('Close: ' + ticker)
        elif  float(elem['positionAmt']) < 0:        
            if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
                exchange.create_market_buy_order(ticker, amount, {'reduceOnly':'true'})
                print('Close: ' + ticker)

def buy(ticker):
    """매수조건 확인 후 매수"""
    usdt_1p = usdt * 0.02 / (2 * get_ATR(ticker, 14))
    amount = round(usdt_1p, 4)
    df = get_ohlcv(ticker, 1)
    global fire, reset
    print(amount)
    if exhighL < get_condition_max_price(ticker, 1, 'high', df):
        #exchange.create_market_buy_order(ticker, amount)
        re_condition = "SELL"
        bought_list.append(ticker)
        time.sleep(2)
        stop(re_condition, ticker)
        print('BUY: ' + ticker)
        fire[ticker] += 1
        reset[ticker] = 1
    elif exlowL > get_condition_min_price(ticker, 1, 'low', df):
        #exchange.create_market_sell_order(ticker, amount)
        re_condition ="BUY"
        bought_list.append(ticker)
        time.sleep(2)
        stop(re_condition, ticker)
        print('SELL: ' + ticker)
        fire[ticker] += 1
        reset[ticker] = 1

def stop(condition, ticker):
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
            ticker = str(elem['symbol']).replace('USDT', '/USDT')
            amount = str(elem['positionAmt']).replace('-', '')
            if condition == 'SELL':
                price = get_current_price(ticker) - 2 * get_ATR(ticker, 14)
            elif condition == 'BUY':
                price = get_current_price(ticker) + 2 * get_ATR(ticker, 14)
            exchange.create_order(ticker, 'STOP', condition, amount, price, {'stopPrice': price, 'reduceOnly':'true'})
            break

def sell(ticker):
    """매수조건 확인 후 매도"""
    balance = exchange.fetch_balance()['info']['positions']
    df = get_ohlcv(ticker, 1)
    side = ""
    global fire, reset
    for elem in balance:
        if ticker.replace('/USDT', 'USDT') == elem['symbol']:
            if  float(elem['positionAmt']) < 0:
                side = 'SELL'
                break
            elif float(elem['positionAmt']) > 0:
                side = 'BUY'
                break
    if exlowS > get_condition_min_price(ticker,1,'low', df) and side == 'BUY':
        for elem in balance:
            if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
                ticker = str(elem['symbol']).replace('USDT', '/USDT')
                amount = str(elem['positionAmt']).replace('-', '')
                exchange.create_market_sell_order(ticker, amount, {'reduceOnly':'true'})
                print('Close: ' + ticker)
                fire[ticker] = 0
                reset[ticker] = 0
                break
    if exhighS < get_condition_max_price(ticker,1,'high', df) and side == 'SELL':
        for elem in balance:
            if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
                ticker = str(elem['symbol']).replace('USDT', '/USDT')
                amount = str(elem['positionAmt']).replace('-', '')
                exchange.create_market_buy_order(ticker, amount, {'reduceOnly':'true'})
                print('Close: ' + ticker)
                fire[ticker] = 0
                reset[ticker] = 0
                break

def update_boughtlist():
    balance = exchange.fetch_balance()['info']['positions']
    global fire, reset
    for elem in balance:
        ticker = str(elem['symbol']).replace('USDT', '/USDT')
        if elem['initialMargin'] == '0':
            if ticker in bought_list:
                order = exchange.fetchOpenOrders(ticker)
                bought_list.remove(ticker)
                for elem in order:
                    exchange.cancel_order(elem['id'], ticker)
                if fire.get(ticker) != 0:
                    fire[ticker] = 0
                    reset[ticker] = 0
                break

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
fire = {}
reset = {}
for ticker in buy_list:
    fire[ticker] = 0
    reset[ticker] = 0
balance = exchange.fetch_balance()['info']['positions']
for elem in balance:
    if elem['initialMargin'] != '0' and ('USDT' in str(elem['symbol'])):
        ticker = str(elem['symbol']).replace('USDT', '/USDT')
        bought_list.append(ticker)
usdt = exchange.fetch_balance()['USDT']['free']
print('start')
while True:
    try:
        mininute = datetime.datetime.now().minute % 5
        second = datetime.datetime.now().second
        print(str(mininute) + ' and ' + str(second))
        if  mininute == 0 and 0 <= second <= 4:
            for ticker in buy_list:
                reset[ticker] = 0
            print('reset')
        if len(bought_list) == 0:
            usdt = exchange.fetch_balance()['USDT']['free']
        for ticker in buy_list:
            dfl, dfs = get_df(ticker, 20, 10, 1)
            exhighL = get_condition_max_price(ticker, 20,'high', dfl)
            exhighS = get_condition_max_price(ticker, 10,'high', dfs)
            exlowL = get_condition_min_price(ticker, 20, 'low', dfl)
            exlowS = get_condition_min_price(ticker, 10, 'low', dfs)
            if ((ticker not in bought_list) or fire.get(ticker) < 4) and reset.get(ticker) == 0:
                print(ticker + 'buy')
                buy(ticker)
            if ticker in bought_list:
                print(ticker + 'sell')
                sell(ticker)
        print('fire: ' + str(fire))
        print('reset: ' + str(reset))
        update_boughtlist()
    except Exception as e:
        print(e)