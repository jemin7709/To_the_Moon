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

def get_noise(ticker, days):
    """k값으로 사용할 노이즈 계산"""
    df = get_ohlcv(ticker, days)
    df['noise'] = 1 - abs(df['open'] - df['close']) / (df['high'] - df['low'])
    noise = df['noise'].rolling(days).mean().iloc[-1]
    return noise

def get_ATR(ticker, days):
    df = get_ohlcv(ticker, days * days)
    close = np.array(df['close'])
    high = np.array(df['high'])
    low = np.array(df['low'])
    ATR = talib. ATR(high, low, close, timeperiod=days)[-1]
    return round(ATR, 4)

def get_target_long_price(ticker):
    df = get_ohlcv(ticker, 2)
    """변동성 돌파 전략으로 매수 목표가 조회"""
    target_price = df.iloc[1]['open'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * get_noise(ticker, 20)
    return target_price

def get_target_short_price(ticker):
    df = get_ohlcv(ticker, 2)
    """변동성 돌파 전략으로 매수 목표가 조회"""
    target_price = df.iloc[1]['open'] - (df.iloc[0]['high'] - df.iloc[0]['low']) * get_noise(ticker, 20)
    return target_price

def get_current_price(ticker):
    """현재가 조회"""
    orderbook = exchange.fetch_order_book(ticker)
    price = orderbook['asks'][0][0]
    return price

def buy(ticker):
    targetLP = get_target_long_price(ticker)
    targetSP = get_target_short_price(ticker)
    curentP = get_current_price(ticker)
    global reset
    print('Long: ' + str(targetLP))
    print('Sohrt: ' + str(targetSP))
    amount = round(usdt * 0.01 / (2 * get_ATR(ticker, 14)), 4)
    if curentP > targetLP:
        #exchange.create_market_buy_order(ticker, amount)
        print('BUY: ' + ticker)
        bought_list.append(ticker)
    elif curentP < targetSP:
        #exchange.create_market_sell_order(ticker, amount)
        print('SELL: ' + ticker)
        bought_list.append(ticker)

def sell():
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        ticker = str(elem['symbol']).replace('USDT', '/USDT')
        amount = float(elem['positionAmt'])
        if 'USDT' in ticker:
            if amount > 0:
                if elem['initialMargin'] != '0':
                    amount = str(amount).replace('-', '')
                    exchange.create_market_sell_order(ticker, amount, {'reduceOnly':'true'})
                    print('Close: ' + ticker)
                    bought_list.remove(ticker)
            elif  amount < 0:        
                if elem['initialMargin'] != '0':
                    amount = str(amount).replace('-', '')
                    exchange.create_market_buy_order(ticker, amount, {'reduceOnly':'true'})
                    print('Close: ' + ticker)
                    bought_list.remove(ticker)

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
usdt = exchange.fetch_balance()['USDT']['free']
balance = exchange.fetch_balance()['info']['positions']

for elem in balance:
    if elem['initialMargin'] != '0' and ('USDT' in str(elem['symbol'])):
        ticker = str(elem['symbol']).replace('USDT', '/USDT')
        bought_list.append(ticker)

print('start')
while True:
    try:
        hour = datetime.datetime.now().hour % 4
        minute = datetime.datetime.now().minute
        second = datetime.datetime.now().second
        print(str(minute) + ' and ' + str(second))
        if len(bought_list) == 0:
            usdt = exchange.fetch_balance()['USDT']['free']
        if  minute == 1 and 1 <= second <= 7:
            sell()
        else:
            for ticker in buy_list:
                if ticker not in bought_list:
                    print(ticker + ' buy')
                    buy(ticker)
    except Exception as e:
        print(e)