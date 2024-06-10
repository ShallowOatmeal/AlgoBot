from ibapi.client import EClient # sending requests to the IB server
from ibapi.wrapper import EWrapper # handling incoming messages
import pandas as pd
import queue

from lightweight_charts import Chart

from ibapi.client import Contract
from threading import Thread

import time, datetime

INITIAL_SYMBOL = 'TSM'
INITIAL_TIMEFRAME = '5 mins'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_CLIENT_ID = 1

LIVE_TRADING = False
LIVE_TRADING_PORT = 7496
PAPER_TRADING_PORT = 7497
TRADING_PORT = PAPER_TRADING_PORT
if LIVE_TRADING:
    TRADING_PORT = LIVE_TRADING_PORT

data_queue = queue.Queue()

class IBClient(EWrapper, EClient):

    def __init__(self, host, port, client_id):
        EClient.__init__(self, self)

        self.connect(host, port, client_id)

        thread = Thread(target=self.run)
        thread.start()

        
    def historicalData(self, req_id, bar):
        print(bar)
        t = datetime.datetime.fromtimestamp(int(bar.date))

        # creation bar dictionary for each bar received 
        
        data = {
            'date': t,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': int(bar.volume)
        }

        print(data)

    # callback when all historical data has been received
        data_queue.put(data)


    def historicalDataEnd(self, reqId, start, end):
        print(f"end of data {start} {end}")
        
        update_chart()


def error(self, req_id, code, msg, misc):
    if code in [2104, 2106, 2158]:
        print(msg)
    else:
        print('Error {}: {}'.format(code, msg))

def update_chart():
    try:
        bars = []
        while True:  # Keep checking the queue for new data
            data = data_queue.get_nowait()
            bars.append(data)
    except queue.Empty:
        print("empty queue")
    finally:
        # once we have received all the data, convert to pandas dataframe
        df = pd.DataFrame(bars)
        print(df)

        # set the data on the chart
        if not df.empty:
            chart.set(df)

            # once we get the data back, we don't need a spinner anymore
            chart.spinner(False)

def on_timeframe_selection(chart):
    print("selected timeframe")
    print(chart.topbar['symbol'].value, chart.topbar['timeframe'].value)
    get_bar_data(chart.topbar['symbol'].value, chart.topbar['timeframe'].value)

def on_search(chart, searched_string):
    get_bar_data(searched_string, chart.topbar['timeframe'].value)
    chart.topbar['symbol'].set(searched_string)

def get_bar_data(symbol, timeframe):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'STK'
    contract.exchange = 'SMART'
    contract.currency = 'USD'
    what_to_show = 'TRADES'

    client.reqHistoricalData(
        2, contract, '', '30 D', timeframe, what_to_show, True, 2, False, []
        )
    
    chart.watermark(symbol)

if __name__ == '__main__':

    client = IBClient(DEFAULT_HOST, TRADING_PORT, DEFAULT_CLIENT_ID)


    time.sleep(1)

    chart = Chart(toolbox=True, width=1000, inner_width=0.6, inner_height=1)

    chart.topbar.textbox('symbol', INITIAL_SYMBOL)
    chart.topbar.switcher('timeframe', ('5 mins', '15 mins', '1 hour'), default= INITIAL_TIMEFRAME, func=on_timeframe_selection)

    chart.events.search += on_search


    get_bar_data(INITIAL_SYMBOL, INITIAL_TIMEFRAME)

    time.sleep(1)

    chart.show(block=True)


