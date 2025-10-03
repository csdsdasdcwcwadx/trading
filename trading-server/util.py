import websocket
import threading
import logging

logger = logging.getLogger(__name__)

clients = {}
maxAmount = 1 # 單次最多交易一顆
arbitrage_lock = threading.Lock()

def check_arbitrage(exchangeName: str):
    with arbitrage_lock:
        ex_names = list(clients.keys())

        best_ask_ex = min(clients, key=lambda ex: clients[ex].ask * (1 + clients[ex].fee) if clients[ex].ask else float("inf")) # 買入ask
        best_bid_ex = max(clients, key=lambda ex: clients[ex].bid * (1 - clients[ex].fee) if clients[ex].bid else 0) # 賣出bid
        calculate_profit(best_ask_ex, best_bid_ex)

        # for other_ex in ex_names:
        #     if exchangeName == other_ex:
        #         continue

        #     # ========== Case 1: exchangeName 買，other_ex 賣 ==========
        #     if calculate_profit(exchangeName, other_ex):
        #         return # 找到套利後直接結束

        #     # ========== Case 2: other_ex 買，exchangeName 賣 ==========
        #     if calculate_profit(other_ex, exchangeName):
        #         return  # 找到套利後直接結束

def calculate_profit(buy_ex, sell_ex):
    buy_ask = clients[buy_ex].ask
    sell_bid = clients[sell_ex].bid
    buy_fee = clients[buy_ex].fee
    sell_fee = clients[sell_ex].fee

    if None in [buy_ask, sell_bid]:
        return False

    cost = buy_ask * (1 + buy_fee)
    revenue = sell_bid * (1 - sell_fee)
    profit = revenue - cost
    amount = min(clients[buy_ex].askDepth, clients[sell_ex].bidDepth, maxAmount)

    if profit > 0:
        if (profit > 1):
            print(cost, revenue)
        return _handle_opportunity(buy_ex, sell_ex, buy_ask, sell_bid, profit, buy_fee, sell_fee)
    else:
        # if buy_ask < sell_bid:
        #     print(f"[無套利] {buy_ex} 買({buy_ask}) → {sell_ex} 賣({sell_bid}), 損益: {profit}")
        return False

def _handle_opportunity(buy_ex, sell_ex, buy_ask, sell_bid, profit, buy_fee, sell_fee):
    # print(f"[套利機會] {buy_ex} 買({buy_ask}) → {sell_ex} 賣({sell_bid}), 利潤: {profit}")
    logger.info(f"[套利機會] {buy_ex} 買({buy_ask}) → {sell_ex} 賣({sell_bid}), 利潤: {profit}")
    clients[buy_ex].ask = None
    clients[sell_ex].bid = None
    return True

    # 🔄 再查一次最新價格
    new_buy_ask = clients[buy_ex].getPrice("ask")
    new_sell_bid = clients[sell_ex].getPrice("bid")

    if new_buy_ask.get('price') and new_sell_bid.get('price'):
        new_buy_ask = float(new_buy_ask['price'])
        new_sell_bid = float(new_sell_bid['price'])

        cost = new_buy_ask * (1 + buy_fee)
        revenue = new_sell_bid * (1 - sell_fee)
        real_profit = revenue - cost

        if real_profit > 0:
            print(f"✅ 確認後套利成立，利潤: {real_profit}")
            return True
        else:
            print(f"❌ 利潤消失，放棄交易 (最新利潤 {real_profit})")
            return False
    else:
        return False

def start_websocket(url, on_message, on_open = None, on_close = None):
    ws = websocket.WebSocketApp(url, on_message=on_message, on_open=on_open, on_close=on_close)
    thread = threading.Thread(target=ws.run_forever, daemon=True)
    thread.start()

    return ws

def init_clients():
    from exchange import Binance, Bitopro, Maxcoin, CoinBase, Pionex, Kraken, MEXC, Bybit, Gate, Bitget, OKX, HTX, BingX
    # clients['bitopro'] = Bitopro()
    clients['binance'] = Binance()
    clients['maxcoin'] = Maxcoin()
    # clients['coinbase'] = CoinBase()
    clients['pionex'] = Pionex()
    clients['kraken'] = Kraken()
    clients['mexc'] = MEXC()
    clients['bybit'] = Bybit()
    clients['gate'] = Gate()
    clients['bitget'] = Bitget()
    clients['okx'] = OKX()
    clients['htx'] = HTX()
    clients['bingx'] = BingX()