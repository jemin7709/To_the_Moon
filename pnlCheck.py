import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
def result(name):
    df = pd.read_excel(name)[::-1]
    df['Date(UTC)'] = pd.to_datetime(df['Date(UTC)'])
    df.set_index('Date(UTC)', inplace=True)
    profit = 0
    loss = 0
    profit_count = 0
    loss_count = 0

    df['real'] = df['Realized Profit'] - df['Fee']
    df['win'] = np.where(df['real'] > 0, 1, 0)
    df['ror'] = df['real'].cumsum()
    lose = df['win'].value_counts()[0]
    win = df['win'].value_counts()[1]
    
    for real in df['real']:
        if real > 0:
            profit += real
            profit_count += 1
        elif real < 0:
            loss += real
            loss_count += 1
    
    avg_profit = profit / profit_count
    avg_loss = loss / loss_count
    profit = round(df['ror'].iloc[-1], 2)
    mdd = round(df['ror'].min(), 2)
    win_late = round(win / (win + lose), 4)
    pnl_ratio = round(avg_profit / abs(avg_loss), 2)
    tpi = round(win_late * (1 + pnl_ratio), 2)
    print('수익: ' + str(profit) + ' USDT')
    print('최대 낙폭: ' + str(mdd) + ' USDT')
    print('승률: ' + str(win_late * 100) + '%')
    print('손익비: ' + str(pnl_ratio))
    print('tpi: ' + str(tpi))
    #print(df)
    #df.to_csv('result.csv')
    plt.plot(df['ror'])
    plt.show()

result('거래 내역 내보내기 (1).xlsx')