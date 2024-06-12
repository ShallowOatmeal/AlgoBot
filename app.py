from ibapi.client import EClient # sending requests to the IB server
from ibapi.wrapper import EWrapper # handling incoming messages
import pandas as pd
import queue

from lightweight_charts import Chart

from ibapi.client import Contract, Order, ScannerSubscription
from ibapi.tag_value import TagValue

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

current_lines = []

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

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.order_id = orderId
        print(f"next valid id is {self.order_id}")


def error(self, req_id, code, msg, misc):
    if code in [2104, 2106, 2158]:
        print(msg)
    else:
        print('Error {}: {}'.format(code, msg))

def update_chart():
    global current_lines

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
            
            chart.horizontal_line(df['high'].max(), func=on_horizontal_line_move)

            # if there were any indicators on the chart already 

            if current_lines:
                for l in current_lines:
                    l.delete()
            
            current_lines = []

            # calculate any new lines to render
            # create a line with SMA label on the chart
            line = chart.create_line(name='SMA 50')
            line.set(pd.DataFrame({
                'time': df['date'],
                f'SMA 50': df['close'].rolling(window=50).mean()
            }).dropna())
            current_lines.append(line)


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


# callback for when user changes position of horizontal line

def on_horizontal_line_move(chart, line):
    print(f'Horizontal line moved to: {line.price}')

def place_order(key):
    symbol = chart.topbar['symbol'].value


    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'STK'
    contract.currency = 'USD'
    contract.exchange = 'SMART'
  

    order = Order()
    order.orderType = 'MKT'
    order.totalQuantity = 1
    order.eTradeOnly = ''
    order.firmQuoteOnly = ''

    client.reqIds(-1)
    time.sleep(2)

    if key == 'O':
        print('buy order')
        order.action = "BUY"

    if key == 'P':
        print("sell order")
        order.action = "SELL"

    if client.order_id:
        print("got order id, placing buy order")
        client.placeOrder(client.order_id, contract, order)

def do_scan(scan_code):
    scannerSubscription = ScannerSubscription()
    scannerSubscription.instrument = "STK"
    scannerSubscription.locationCode = "STK.US.MAJOR"
    scannerSubscription.scanCode = scan_code

    tagValues = []

    tagValues.append(TagValue("optVolumeAbove", "1000"))
    tagValues.append(TagValue("avgVolumeAbove", "10000"))

    client.reqScannerSubscription(7002, scannerSubscription, [], tagValues)
    time.sleep(1)

    display_scan()

    client.cancelScannerSubscription(7002)


def take_screenshot(key):
    img = chart.screenshot()
    t = time.time()
    with open(f"screenshot -{t}.png", 'wb') as f:
        f.write(img)

def display_scan():
    def on_row_click(row):
        chart.topbar['symbol'].set(row['symbol'])
        get_bar_data(row['symbol', '5 mins'])

            # create table on the UI, pass callback function for when a row is clicked
        table = chart.create_table(
            width=0.4,
            height=0.5,
            headings=('symbol', 'value'),
            widths=(0.7, 0.3),
            alignments=('left','center'),
            position='left', func=on_row_click
        )

        # poll queue for any new scan results

        try:
            while True:
                data = data_queue.get_nowait()
                table.new_row(data['symbol'], '')
        except queue.Empty:
            print('empty queue')
        finally:
            print("done")



if __name__ == '__main__':

    client = IBClient(DEFAULT_HOST, TRADING_PORT, DEFAULT_CLIENT_ID)


    time.sleep(1)

    chart = Chart(toolbox=True, width=1000, inner_width=0.6, inner_height=1)

    chart.topbar.textbox('symbol', INITIAL_SYMBOL)
    chart.topbar.switcher('timeframe', ('5 mins', '15 mins', '1 hour'), default= INITIAL_TIMEFRAME, func=on_timeframe_selection)

    chart.hotkey('shift','O', place_order) #buy order

    chart.hotkey('shift','P', place_order) #sell oder

    chart.events.search += on_search


    get_bar_data(INITIAL_SYMBOL, INITIAL_TIMEFRAME)

    time.sleep(1)

    chart.topbar.button('screenshot', 'Screenshot', func=take_screenshot)

    do_scan("HOT_BY_VOLUME")

    chart.show(block=True)



## FIX -- ORDER PLACING. AND THE SCANNER. TWO ISSUES, REST IS OK!
