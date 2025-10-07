import websocket
import threading
import logging
import asyncio

logger = logging.getLogger(__name__)

clients = {}
safe_ratio = 0.9
arbitrage_lock = threading.Lock()

def check_arbitrage(exchangeName: str):
    with arbitrage_lock:
        # ex_names = list(clients.keys())

        best_ask_ex = min(clients, key=lambda ex: clients[ex].ask * (1 + clients[ex].fee) if clients[ex].ask else float("inf")) # 買入ask
        best_bid_ex = max(clients, key=lambda ex: clients[ex].bid * (1 - clients[ex].fee) if clients[ex].bid else 0)
        # if best_ask_ex == 'mexc':
        #     best_bid_ex = 'kraken'
        # else:
        #     best_bid_ex = 'mexc'
        calculate_profit(best_ask_ex, best_bid_ex)

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

    if profit > 0:
        # logger.info(f"[套利機會] {buy_ex} 買({buy_ask}) → {sell_ex} 賣({sell_bid}), 利潤: {profit}")
        asyncio.run(_handle_opportunity(buy_ex, sell_ex, buy_ask, sell_bid, profit, buy_fee, sell_fee))
    else:
        if buy_ask < sell_bid:
            print(f"[無套利] {buy_ex} 買({buy_ask}) → {sell_ex} 賣({sell_bid}), 損益: {profit}")
        return False

async def _handle_opportunity(buy_ex, sell_ex, buy_ask, sell_bid, profit, buy_fee, sell_fee):
    clients[buy_ex].ask = None
    clients[sell_ex].bid = None

    # 🔄 再查一次最新價格
    new_buy_ask, new_sell_bid = await asyncio.gather(
        clients[buy_ex].getPrice("ask"),
        clients[sell_ex].getPrice("bid")
    )
    if not (new_buy_ask.get('price') and new_sell_bid.get('price')):
        return False

    new_buy_ask = float(new_buy_ask['price'])
    new_sell_bid = float(new_sell_bid['price'])

    cost = new_buy_ask * (1 + buy_fee)
    revenue = new_sell_bid * (1 - sell_fee)
    real_profit = revenue - cost
    amount = min(clients[buy_ex].askDepth, clients[sell_ex].bidDepth) * safe_ratio
    amount = min(amount, 1)

    if real_profit <= 0:
        print(f"❌ 利潤消失，放棄交易 (最新利潤 {real_profit})")
        return False
    
    logger.info(f"[套利機會] {amount}顆 {buy_ex} 買({new_buy_ask}) → {sell_ex} 賣({new_sell_bid}), 利潤: {profit * amount}") # 理想套利

    buy_result, sell_result = await placeOrder(buy_ex, sell_ex, new_buy_ask, new_sell_bid, amount) # 實際下單
    if not (buy_result.get("isSuccess") and sell_result.get("isSuccess")):
        logger.warning("❌ 下單失敗，嘗試撤銷未成交訂單")

        if buy_result.get("isSuccess"):
            await safe_recover_order(
                exchange=clients[buy_ex],
                side="buy",
                order_id=buy_result["orderID"],
                amount=amount
            )
        if sell_result.get("isSuccess"):
            await safe_recover_order(
                exchange=clients[sell_ex],
                side="sell",
                order_id=sell_result["orderID"],
                amount=amount
            )
        return False
    
    buy_order, sell_order = await checkOrder(buy_ex, sell_ex, buy_result["orderID"], sell_result["orderID"])
    if not (buy_order['isFilled'] and sell_order['isFilled']):
        logger.warning("⚠️ 訂單未完全成交，嘗試撤單")
        if not buy_order['isFilled']:
            await safe_recover_order(
                exchange=clients[buy_ex],
                side="buy",
                order_id=buy_result["orderID"],
                amount=amount
            )
        if not sell_order['isFilled']:
            await safe_recover_order(
                exchange=clients[sell_ex],
                side="sell",
                order_id=sell_result["orderID"],
                amount=amount
            )
        return False
    
    actual_buy_price = buy_order['price']
    actual_sell_price = sell_order['price']

    final_cost = actual_buy_price * (1 + buy_fee)
    final_revenue = actual_sell_price * (1 - sell_fee)
    final_profit = final_revenue - final_cost

    if final_profit > 0:
        logger.info(f"✅ 套利成功! 實際利潤: {final_profit}")
    else:
        logger.warning(f"⚠️ 成交後無利潤 (實際: {final_profit})")

async def placeOrder(buy_ex, sell_ex, buy_ask, sell_bid, amount):
    results = await asyncio.gather(
        clients[buy_ex].order('buy', amount, buy_ask),
        clients[sell_ex].order('sell', amount, sell_bid)
    )

    return results

async def checkOrder(buy_ex, sell_ex, buy_orderId, sell_orderId):
    results = await asyncio.gather(
        clients[buy_ex].query_order(buy_orderId),
        clients[sell_ex].query_order(sell_orderId)
    )

    return results

async def safe_recover_order(exchange, side, order_id, amount, retry_limit=3, retry_delay=1.0):
    opposite_side = 'sell' if side == 'buy' else 'buy'

    try:
        if await exchange.cancel_order(order_id):
            # logging.info(f"✅ {exchange.name} 訂單 {order_id} 已成功取消")
            return True
        else:
            # logging.warning(f"⚠️ {exchange.name} 訂單 {order_id} 無法取消，可能已成交，進入止損程序")
            # 立即取得對向價格
            price_side = "bid" if opposite_side == "sell" else "ask"
            
            for attempt in range(1, retry_limit + 1):
                # logging.info(f"🚨 嘗試第 {attempt} 次止損單：{exchange.name} {opposite_side} {amount} @ {market_price}")
                market_price = exchange.getattr(price_side)
                order_res = await exchange.order(opposite_side, amount, market_price)
                order_id = order_res.get("orderID")

                # 確認是否成交
                await asyncio.sleep(retry_delay)
                order = await exchange.query_order(order_id)

                if order.get("isFilled"):
                    # 止損對沖成功
                    return True
                else:
                    # logging.warning(f"⏳ 止損單未成交，嘗試撤銷再重下")
                    if await exchange.cancel_order(order_id):
                        return True

            return False

    except Exception as e:
        return False

async def balanceAccount():
    print('balance')

def start_websocket(url, on_message, on_open = None, on_close = None):
    ws = websocket.WebSocketApp(url, on_message=on_message, on_open=on_open, on_close=on_close)
    thread = threading.Thread(target=ws.run_forever, daemon=True)
    thread.start()

    return ws

def init_clients():
    from exchange import Binance, Bitopro, Maxcoin, CoinBase, Pionex, Kraken, MEXC, Bybit, Gate, Bitget, OKX, HTX, BingX
    # clients['bitopro'] = Bitopro()
    # clients['binance'] = Binance()
    # clients['maxcoin'] = Maxcoin()
    # # clients['coinbase'] = CoinBase()
    # clients['pionex'] = Pionex()
    clients['kraken'] = Kraken()
    clients['mexc'] = MEXC()
    # clients['bybit'] = Bybit()
    # clients['gate'] = Gate()
    # clients['bitget'] = Bitget()
    # clients['okx'] = OKX()
    # clients['htx'] = HTX()
    # clients['bingx'] = BingX()