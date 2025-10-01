import requests
import json
import hmac
import hashlib
import base64
import time
from urllib.parse import urlencode
import uuid
from util import check_arbitrage, start_websocket
import websocket
from mexcproto import PushDataV3ApiWrapper_pb2
import gzip
# from cdp.auth.utils.jwt import generate_jwt, JwtOptions

with open('../config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Priority = config["Priority"]
exchange_type = "MARKET"
default_currency = 'eth'
fee = {
    'binance': 0,
    'bitopro': 0,
    'maxcoin': 0,
    'pionex': 0,
    'kraken': 0,
    "mexc": 0,
    'bybit': 0,
    'gate': 0,
    'bitget': 0,
    'okx': 0,
    'htx': 0,
}

class Binance:
    def __init__(self):
        data = config["Binance"]

        self.__base_url = "https://api.binance.com"
        self.__API_Key = data["API_Key"]
        self.__Secret_Key = data["Secret_Key"]
        self.currency = default_currency
        self.ws = None
        self.limit = {
            "price_limit": [],
            "amount_limit": [],
            "notional_limit": []
        }

        self.ask = None
        self.bid = None
        self.fee = fee['binance']
        self.askDepth = 0
        self.bidDepth = 0

    def order(self, action: str, amount: str, price = '1'):
        response = self.__sendRequest("POST", "/api/v3/order", {
            "symbol": f"{self.currency.upper()}USDT",
            "side": action,
            "type": exchange_type, # LIMIT or MARKET,
            "quantity": amount,
            # "price": price,
            # "timeInForce": "GTC"
        }).json()

        return {
            "isSuccess": bool(response.get('orderId')),
            "response": response
        }

    def cancel_order(self, orderId: str):
        response = self.__sendRequest("DELETE", "/api/v3/order", {
            "symbol": f"{self.currency.upper()}USDT",
            "orderId": orderId,
        })
        return response.json()

    def account(self):
        response = self.__sendRequest("GET", "/api/v3/account", {})
        return response.json()["balances"] # 顯示所有幣種餘額

    def limitation(self):
        url = self.__base_url + f"/api/v3/exchangeInfo?symbol={self.currency.upper()}USDT"
        response = requests.get(url).json()["symbols"][0]['filters']

        data = {
            "price_limit": [],
            "amount_limit": [],
            "notional_limit": []
        }

        for condition in response:
            match condition['filterType']:
                case 'LOT_SIZE':
                    data['amount_limit'] = [
                        condition['minQty'],
                        condition['maxQty']
                    ]
                case 'PRICE_FILTER':
                    data['price_limit'] = [
                        condition['minPrice'],
                        condition['maxPrice']
                    ]
                case 'NOTIONAL':
                    data['notional_limit'] = [
                        condition['minNotional'],
                        condition['maxNotional']
                    ]

        return data

    def start_ws(self):
        self.limit = self.limitation()

        def on_message(ws, msg):
            data = json.loads(msg)
            self.ask = float(data["a"][0][0])
            self.bid = float(data["b"][0][0])
            self.askDepth = float(data["a"][0][1])
            self.bidDepth = float(data["b"][0][1])
            # print('-------binance-------')
            check_arbitrage('binance')

            # print(f"Best Bid: {self.bid}, Best Ask: {self.ask}")

        self.ws = start_websocket(url=f"wss://stream.binance.com:9443/ws/{self.currency}usdt@depth", on_message=on_message)

    def stop_ws(self):
        if self.ws:
            self.ws.close()

    def getPrice(self, action):
        url = self.__base_url + f"/api/v3/ticker/bookTicker?symbol={self.currency.upper()}USDT"
        response = requests.get(url).json()
        return {
            'amount': response[f'{action}Qty'],
            'price': response[f'{action}Price']
        }

    def __sendRequest(self, method: str, endpoint: str, params: dict):
        params["timestamp"] = int(time.time() * 1000)
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])

        signature = hmac.new(
            self.__Secret_Key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        headers = {"X-MBX-APIKEY": self.__API_Key}
        url = self.__base_url + endpoint

        if method == "GET":
            res = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            res = requests.post(url, headers=headers, params=params)
        elif method == "DELETE":
            res = requests.delete(url, headers=headers, params=params)
        else:
            raise ValueError("Unsupported HTTP method")

        return res

class Bitopro:
    def __init__(self):
        data = config["Bitopro"]

        self.__base_url = "https://api.bitopro.com/v3"
        self.__API_Key = data["API_Key"]
        self.__Secret_Key = data["Secret_Key"]
        self.currency = default_currency
        self.ws = None
        self.limit = {
            "price_limit": [],
            "amount_limit": [],
            "notional_limit": []
        }

        self.ask = None
        self.bid = None
        self.fee = fee['bitopro']
        self.askDepth = 0
        self.bidDepth = 0
    
    def order(self, action: str, amount: str, price = '0'):
        response = self.__sendRequest("POST", f"/orders/{self.currency}_usdt", {
            "action": action,
            "amount": amount,
            "type": exchange_type, # LIMIT or MARKET or STOP_LIMIT
            # "price": price,
            # "timeInForce": "POST_ONLY"
        }).json()

        return {
            "isSuccess": bool(response.get('orderId')),
            "response": response
        }

    def cancel_order(self, orderId: str):
        response = self.__sendRequest("DELETE", f"/orders/{self.currency.upper()}_USDT/{orderId}", {})
        return response.json()

    def account(self):
        response = self.__sendRequest("GET", "/accounts/balance", {})
        return response.json()

    def limitation(self):
        url = self.__base_url + "/provisioning/trading-pairs"
        response = requests.get(url)

        data = {
            "price_limit": [],
            "amount_limit": [],
            "notional_limit": []
        }
        
        for crypto in response.json()["data"]:
            if crypto["pair"] == f"{self.currency}_usdt":
                data['amount_limit'].append(crypto['minLimitBaseAmount'])
                data['amount_limit'].append(crypto['maxLimitBaseAmount'])
                data['notional_limit'].append(crypto['minMarketBuyQuoteAmount'])

                return data
            
    def start_ws(self):
        self.limit = self.limitation()

        def on_message(ws, msg):
            data = json.loads(msg)
            self.ask = float(data["asks"][0]["price"])
            self.bid = float(data["bids"][0]["price"])
            self.askDepth = float(data["asks"][0]["total"])
            self.bidDepth = float(data["bids"][0]["total"])
            # print('-------bitopro-------')
            check_arbitrage('bitopro')

            # print(f"Best Bid: {self.bid}, Best Ask: {self.ask}")

        self.ws = start_websocket(url=f"wss://stream.bitopro.com:443/ws/v1/pub/order-books/{self.currency}_USDT", on_message=on_message)

    def stop_ws(self):
        if self.ws:
            self.ws.close()

    def getPrice(self, action):
        url = self.__base_url + f"/order-book/{self.currency}_usdt?limit=1"
        response = requests.get(url).json()[f"{action}s"][0]
        return {
            'amount': response['amount'],
            'price': response['price']
        }

    def __sendRequest(self, method: str, endpoint: str, params: dict):
        params["timestamp"] = int(time.time() * 1000)
        params["nonce"] = int(time.time() * 1000)
        payload = base64.urlsafe_b64encode(json.dumps(params).encode("utf-8")).decode("utf-8")

        signature = hmac.new(
            self.__Secret_Key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha384
        ).hexdigest()

        headers = {
            "X-BITOPRO-APIKEY": self.__API_Key,
            "X-BITOPRO-PAYLOAD": payload,
            "X-BITOPRO-SIGNATURE": signature,
        }

        url = self.__base_url + endpoint

        if method == "GET":
            res = requests.get(url, headers=headers)  # GET 時 params 應該在 payload 內，而不是 query string
        elif method == "POST":
            res = requests.post(url, headers=headers, json=params) # POST 也是一樣
        elif method == "DELETE":
            res = requests.delete(url, headers=headers)
        else:
            raise ValueError("Unsupported HTTP method")

        return res

class Maxcoin:
    def __init__(self):
        data = config["Maxcoin"]

        self.__base_url = "https://max-api.maicoin.com"
        self.__API_Key = data["API_Key"]
        self.__Secret_Key = data["Secret_Key"]
        self.currency = default_currency
        self.ws = None
        self.limit = {
            "price_limit": [],
            "amount_limit": [],
            "notional_limit": []
        }

        self.ask = None
        self.bid = None
        self.fee = fee['maxcoin']
        self.askDepth = 0
        self.bidDepth = 0

    def order(self, action: str, amount: str, price = '0'):
        response = self.__sendRequest("POST", "/api/v3/wallet/spot/order", {
            'market': f"{self.currency}usdt",
            'side': action.lower(),
            'volume': amount,
            # 'price': price,
            'client_oid': str(uuid.uuid4()),
            'ord_type': exchange_type.lower(),
        })
        return {
            "isSuccess": bool(response.get('id')),
            "response": response
        }
    
    def cancel_order(self, orderId: str):
        response = self.__sendRequest("DELETE", "/api/v3/order", {
            'id': orderId,
        })
        return response.json()

    def account(self):
        response = self.__sendRequest("GET", "/api/v3/wallet/spot/accounts", {})
        return response.json()["balances"] # 顯示所有幣種餘額

    def limitation(self):
        url = self.__base_url + f"/api/v3/markets"
        response = requests.get(url).json()

        data = {
            "price_limit": [],
            "amount_limit": [],
            "notional_limit": []
        }

        for condition in response:
            if condition['id'] == f"{self.currency}usdt":
                data['notional_limit'].append(condition['min_quote_amount'])
                data['amount_limit'].append(condition['min_base_amount'])

        return data

    def start_ws(self):
        self.limit = self.limitation()

        def on_message(ws, msg):
            data = json.loads(msg)

            if data.get('a') and len(data['a']):
                self.ask = float(data['a'][0][0])
                self.askDepth = float(data['a'][0][1])

            if data.get('b') and len(data['b']):
                self.bid = float(data['b'][0][0])
                self.bidDepth = float(data['b'][0][1])

            # print('-------maxcoin-------')
            check_arbitrage('maxcoin')
            # print(f"Best Bid: {self.bid}, Best Ask: {self.ask}")

        def on_open(ws):
            subscribe_msg = {
                "action": "sub",
                "subscriptions": [
                    {"channel": "book", "market": f"{self.currency}usdt", "depth": 1},
                ],
                "id": "client1"
            }
            ws.send(json.dumps(subscribe_msg))

        self.ws = start_websocket(url="wss://max-stream.maicoin.com/ws", on_message=on_message, on_open=on_open)

    def stop_ws(self):
        if self.ws:
            self.ws.close()

    def getPrice(self, action):
        url = f"{self.__base_url}/api/v3/depth?market={self.currency}usdt"
        response = requests.get(url).json()[f'{action}s']

        if action == 'bid':
            data = response[0]
        else:
            data = response[len(response) - 1]

        return {
            'amount': data[1],
            'price': data[0]
        }
    
    def __sendRequest(self, method: str, endpoint: str, params: dict):
        payload_dict = {
            "nonce": int(time.time() * 1000),
            "path": endpoint
        }

        json_str = json.dumps(payload_dict)  # 轉換為 JSON 字符串
        payload = base64.b64encode(json_str.encode()).decode()

        signature = hmac.new(
            self.__Secret_Key.encode("utf-8"),           # 使用 Secret Key 作為密鑰
            payload.encode(),              # 對 payload 進行簽名
            hashlib.sha256                 # 使用 HMAC-SHA256 演算法
        ).hexdigest()

        headers = {
            'X-MAX-ACCESSKEY': self.__API_Key,     # 添加 Access Key
            'X-MAX-PAYLOAD': payload,          # 添加 payload
            'X-MAX-SIGNATURE': signature,      # 添加簽名
            'Content-Type': 'application/json'
        }

        url = self.__base_url + endpoint

        if method == 'GET':
            url += f"?{urlencode(params)}"
            res = requests.get(url, headers=headers)
        else:
            res = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=json.dumps(params)
            )

        return res
    
class CoinBase:
    def __init__(self):
        data = config["Coinbase"]

        # self.__base_url = "https://max-api.maicoin.com"
        # self.__API_Key = data["API_Key"]
        # self.__Secret_Key = data["Secret_Key"]
        self.ws = None

        self.ask = None
        self.bid = None
        self.fee = 0.001
        self.askDepth = 0
        self.bidDepth = 0

    def start_ws(self, currency: str):
        def on_message(ws, msg):
            data = json.loads(msg)
            if data['type'] == 'ticker':
                print(data)
                # self.ask = float(data["asks"][0]["price"])
                # self.bid = float(data["bids"][0]["price"])
                # self.askDepth = float(data["asks"][0]["total"])
                # self.bidDepth = float(data["bids"][0]["total"])
                # check_arbitrage('coinbase')

                # print(f"Best Bid: {self.bid}, Best Ask: {self.ask}")

        def on_open(ws):
            subscribe_msg = {
                "type": "subscribe",
                "product_ids": ["ETH-USDT"],
                "channels": [
                    "level2",
                    "heartbeat",
                    {
                        "name": "ticker",
                        "product_ids": ["ETH-USDT"]
                    }
                ]
            }
            ws.send(json.dumps(subscribe_msg))

        self.ws = start_websocket(url="wss://ws-feed.exchange.coinbase.com", on_message=on_message, on_open=on_open)

    def stop_ws(self):
        if self.ws:
            self.ws.close()

class Pionex:
    def __init__(self):
        data = config["Pionex"]
        self.ws = None

        self.__base_url = "https://api.pionex.com"
        self.__API_Key = data["API_Key"]
        self.__Secret_Key = data["Secret_Key"]
        self.currency = default_currency
        self.ws = None
        self.limit = {
            "price_limit": [],
            "amount_limit": [],
            "notional_limit": []
        }

        self.ask = None
        self.bid = None
        self.fee = fee['pionex']
        self.askDepth = 0
        self.bidDepth = 0
    
    def order(self, action: str, amount: str, price = '0'):
        response = self.__sendRequest("POST", "/api/v1/trade/order", body={
            "symbol": f"{self.currency.upper()}_USDT",
            "amount": amount,
            "side": action.upper(),
            "type": exchange_type.upper(),
            # "price": price,
        })
        return response.json()

    def cancel_order(self, orderId: str):
        response = self.__sendRequest("DELETE", "/api/v1/trade/order", {

        })
        return response.json()
    
    def account(self):
        response = self.__sendRequest("GET", "/api/v1/account/balances")
        return response.json() # 顯示所有幣種餘額
    
    def limitation(self):
        url = self.__base_url + "/api/v1/common/symbols"
        response = requests.get(url).json()

        data = {
            "price_limit": [],
            "amount_limit": [],
            "notional_limit": []
        }

        for condition in response['data']['symbols']:
            if condition['symbol'] == f"{self.currency.upper()}_USDT":
                data['amount_limit'].append(condition['minAmount'])
                data['amount_limit'].append(condition['maxTradeSize'])

                data['notional_limit'].append(condition['minTradeDumping'])
                data['notional_limit'].append(condition['maxTradeDumping'])

        return data

    def __sendRequest(self, method: str, endpoint: str, params: dict = {}, body: dict = None):
        # 加入 timestamp
        params["timestamp"] = int(time.time() * 1000)
        signature = self.__sign(method, endpoint, params, body)

        # Header
        headers = {
            "PIONEX-KEY": self.__API_Key,
            "PIONEX-SIGNATURE": signature,
            "Content-Type": "application/json"
        }
        url = self.__base_url + endpoint + "?" + self.__build_sorted_query(params)

        # 發送請求
        if method == "GET":
            res = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            res = requests.post(url, headers=headers, json=body or {}, timeout=10)
        elif method == "DELETE":
            res = requests.delete(url, headers=headers, json=body or {}, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")

        res.raise_for_status()
        return res

    def __build_sorted_query(self, params: dict) -> str:
        items = sorted((k, str(v)) for k, v in params.items())
        return "&".join(f"{k}={v}" for k, v in items)

    def __sign(self, method: str, endpoint: str, query_params: dict, body: dict | None) -> str:
        sorted_q = self.__build_sorted_query(query_params)
        path_url = f"{endpoint}?{sorted_q}"
        msg = f"{method}{path_url}"

        if body:
            body_text = json.dumps(body, separators=(", ", ": "))  # 穩定 JSON
            msg += body_text
        
        return hmac.new(self.__Secret_Key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()

    def start_ws(self):
        self.limit = self.limitation()

        def on_message(ws, msg):
            data = json.loads(msg)

            if data.get('data'):
                self.ask = float(data['data']["asks"][0][0])
                self.bid = float(data['data']['bids'][0][0])
                self.askDepth = float(data['data']["asks"][0][1])
                self.bidDepth = float(data['data']["bids"][0][1])
                # print('-------pionex-------')
                check_arbitrage('pionex')

                # print(f"Best Bid: {self.bid}, Best Ask: {self.ask}")

        def on_open(ws):
            subscribe_msg = {
                "op": "SUBSCRIBE",
                "topic":  "DEPTH", 
                "symbol": f"{self.currency.upper()}_USDT",
                "limit":  5
            }

            ws.send(json.dumps(subscribe_msg))

        def on_close(ws, close_status_code, close_msg):
            print("WS pionex closed, reconnecting...")
            time.sleep(1)
            self.start_ws()  # 自動重連

        self.ws = start_websocket(
            url="wss://ws.pionex.com/wsPub",
            on_message=on_message,
            on_open=on_open,
            on_close=on_close
        )

    def stop_ws(self):
        if self.ws:
            self.ws.close()

    def getPrice(self, action):
        url = f"{self.__base_url}/api/v1/market/depth?symbol={self.currency.upper()}_USDT&limit=1"
        response = requests.get(url).json()['data'][f'{action}s']

        return {
            'amount': response[0][1],
            'price': response[0][0]
        }

class Kraken:
    def __init__(self):
        data = config["Kraken"]
        self.ws = None

        # self.__base_url = "https://api.pionex.com"
        self.__API_Key = data["API_Key"]
        self.__Secret_Key = data["Secret_Key"]
        self.currency = default_currency
        self.ws = None
        self.limit = {
            "price_limit": [],
            "amount_limit": [],
            "notional_limit": []
        }

        self.ask = None
        self.bid = None
        self.fee = fee['kraken']
        self.askDepth = 0
        self.bidDepth = 0

    def start_ws(self):
        # self.limit = self.limitation()
        def on_open(ws: websocket):
            subscribe_msg = {
                "method": "subscribe",
                "params": {
                    "channel": "ticker",
                    "symbol": [
                        f"{self.currency.upper()}/USDT",
                    ],
                    "event_trigger": "bbo"
                }
            }

            ws.send(json.dumps(subscribe_msg))

        def on_message(ws, msg):
            data = json.loads(msg)
            
            if data.get('data'):
                data = data['data'][0]
                
                if data.get('ask'):
                    self.ask = data['ask']
                    self.askDepth = data['ask_qty']

                if data.get('bid'):
                    self.bid = data['bid']
                    self.bidDepth = data['bid_qty']

                # print('-------kraken-------')
                check_arbitrage('kraken')

                # print(f"Best Bid: {self.bid}, Best Ask: {self.ask}")

        self.ws = start_websocket(url="wss://ws.kraken.com/v2", on_message=on_message, on_open=on_open)

class MEXC:
    def __init__(self):
        data = config["MEXC"]
        self.ws = None

        self.__API_Key = data["API_Key"]
        self.__Secret_Key = data["Secret_Key"]
        self.currency = default_currency
        self.limit = {
            "price_limit": [],
            "amount_limit": [],
            "notional_limit": []
        }

        self.ask = None
        self.bid = None
        self.fee = fee['mexc']
        self.askDepth = 0
        self.bidDepth = 0

    def start_ws(self):
        def on_open(ws):
            subscribe_msg = {
                "method": "SUBSCRIPTION",
                "params": [
                    f"spot@public.limit.depth.v3.api.pb@{self.currency.upper()}USDT@5"
                ]
            }
            ws.send(json.dumps(subscribe_msg))

        def on_message(ws, msg):
            if isinstance(msg, str):
                # 處理 JSON 訊息
                print(f"📩 JSON 訊息: {msg}")
                return
            
            if isinstance(msg, bytes):
                # 嘗試解析為 JSON (某些交易所用 JSON 包裹)
                try:
                    text = msg.decode('utf-8')
                    json_data = json.loads(text)
                    print(f"📩 JSON 數據: {json_data}")
                    return
                except:
                    pass  # 不是 JSON,繼續解析 protobuf

            wrapper = PushDataV3ApiWrapper_pb2.PushDataV3ApiWrapper()
            wrapper.ParseFromString(msg)
            best_ask = wrapper.publicLimitDepths.asks[0]
            best_bid = wrapper.publicLimitDepths.bids[0]

            self.ask = best_ask.price
            self.askDepth = best_ask.quantity
            self.bid = best_bid.price
            self.bidDepth = best_bid.quantity

            # check_arbitrage('mexc')
            # print(f"Best Bid: {self.bid}, Best Ask: {self.ask}")

        self.ws = start_websocket(
            url="wss://wbs-api.mexc.com/ws",
            on_message=on_message,
            on_open=on_open
        )

class Bybit:
    def __init__(self):
        data = config["Bybit"]
        self.ws = None
        self.__API_Key = data["API_Key"]
        self.__Secret_Key = data["Secret_Key"]
        self.currency = default_currency
        self.limit = {"price_limit": [], "amount_limit": [], "notional_limit": []}
        self.ask = None
        self.bid = None
        self.fee = fee['bybit']
        self.askDepth = 0
        self.bidDepth = 0

    def start_ws(self):
        def on_open(ws):
            subscribe_msg = {"op": "subscribe", "args": [f"orderbook.1.{self.currency.upper()}USDT"]}
            ws.send(json.dumps(subscribe_msg))

        def on_message(ws, msg):
            data = json.loads(msg)

            if "data" in data:
                depth = data["data"]
                if "a" in depth and depth["a"]:
                    self.ask = depth["a"][0][0]
                    self.askDepth = depth["a"][0][1]
                if "b" in depth and depth["b"]:
                    self.bid = depth["b"][0][0]
                    self.bidDepth = depth["b"][0][1]
                # check_arbitrage("bybit")
                # print(f"Best Bid: {self.bid}, Best Ask: {self.ask}")

        self.ws = start_websocket(url="wss://stream.bybit.com/v5/public/spot", on_message=on_message, on_open=on_open)

class Gate:
    def __init__(self):
        data = config["Gate"]
        self.ws = None
        self.__API_Key = data["API_Key"]
        self.__Secret_Key = data["Secret_Key"]
        self.currency = default_currency
        self.limit = {"price_limit": [], "amount_limit": [], "notional_limit": []}
        self.ask = None
        self.bid = None
        self.fee = fee['gate']
        self.askDepth = 0
        self.bidDepth = 0

    def start_ws(self):
        def on_open(ws):
            subscribe_msg = {
                "time": int(time.time()),
                "channel": "spot.book_ticker",
                "event": "subscribe",
                "payload": [f"{self.currency.upper()}_USDT"]
            }
            ws.send(json.dumps(subscribe_msg))

        def on_message(ws, msg):
            data = json.loads(msg)

            if data.get("result"):
                depth = data["result"]
                if "a" in depth and depth["a"]:
                    self.ask = depth["a"]
                    self.askDepth = depth["A"]
                if "b" in depth and depth["b"]:
                    self.bid = depth["b"]
                    self.bidDepth = depth["B"]
                # check_arbitrage("gate")
                # print(f"Best Bid: {self.bid}, Best Ask: {self.ask}")


        self.ws = start_websocket(url="wss://api.gateio.ws/ws/v4/", on_message=on_message, on_open=on_open)

class Bitget:
    def __init__(self):
        data = config["Bitget"]
        self.ws = None
        self.__API_Key = data["API_Key"]
        self.__Secret_Key = data["Secret_Key"]
        self.currency = default_currency
        self.limit = {"price_limit": [], "amount_limit": [], "notional_limit": []}
        self.ask = None
        self.bid = None
        self.fee = fee['bitget']
        self.askDepth = 0
        self.bidDepth = 0

    def start_ws(self):
        def on_open(ws):
            subscribe_msg = {"op": "subscribe", "args": [{"instType": "SPOT", "channel": "ticker", "instId": f"{self.currency.upper()}USDT"}]}
            ws.send(json.dumps(subscribe_msg))

        def on_message(ws, msg):
            data = json.loads(msg)
            if "data" in data:
                depth = data["data"][0]
                if "askPr" in depth and depth["askPr"]:
                    self.ask = depth["askPr"]
                    self.askDepth = depth["askSz"]
                if "bidPr" in depth and depth["bidPr"]:
                    self.bid = depth["bidPr"]
                    self.bidDepth = depth["bidSz"]
                # check_arbitrage("bitget")
                # print(f"Best Bid: {self.bid}, Best Ask: {self.ask}")

        self.ws = start_websocket(url="wss://ws.bitget.com/v2/ws/public", on_message=on_message, on_open=on_open)

class OKX:
    def __init__(self):
        data = config["OKX"]
        self.ws = None
        self.__API_Key = data["API_Key"]
        self.__Secret_Key = data["Secret_Key"]
        self.currency = default_currency
        self.limit = {"price_limit": [], "amount_limit": [], "notional_limit": []}
        self.ask = None
        self.bid = None
        self.fee = fee['okx']
        self.askDepth = 0
        self.bidDepth = 0

    def start_ws(self):    
        def on_open(ws):
            subscribe_msg = {
                "op": "subscribe",
                "args": [
                    {
                        "channel": "books",
                        "instType": "SPOT",
                        "instId": f"{self.currency.upper()}-USDT"
                    }
                ]
            }
            ws.send(json.dumps(subscribe_msg))

        def on_message(ws, msg):
            data = json.loads(msg)
            if "data" in data:
                depth = data["data"][0]
                if "asks" in depth and depth["asks"]:
                    self.ask = depth["asks"][0][0]
                    self.askDepth = depth["asks"][0][1]
                if "bids" in depth and depth["bids"]:
                    self.bid = depth["bids"][0][0]
                    self.bidDepth = depth["bids"][0][1]
                # check_arbitrage("okx")
                # print(f"Best Bid: {self.bid}, Best Ask: {self.ask}")

        self.ws = start_websocket(url="wss://ws.okx.com:8443/ws/v5/public", on_message=on_message, on_open=on_open)

class HTX:
    def __init__(self):
        data = config["HTX"]
        self.ws = None
        self.__API_Key = data["API_Key"]
        self.__Secret_Key = data["Secret_Key"]
        self.currency = default_currency
        self.limit = {"price_limit": [], "amount_limit": [], "notional_limit": []}
        self.ask = None
        self.bid = None
        self.fee = fee['htx']
        self.askDepth = 0
        self.bidDepth = 0

    def start_ws(self):
        def on_close(ws, close_status_code, close_msg):
            print("WS htx closed, reconnecting...")
            time.sleep(1)
            self.start_ws()  # 自動重連
    
        def on_open(ws):
            subscribe_msg = {"sub": f"market.{self.currency.lower()}usdt.depth.step0", "id": "id1"}
            ws.send(json.dumps(subscribe_msg))

        def on_message(ws, msg):
            message = json.loads(gzip.decompress(msg).decode("utf-8"))
            if "tick" in message:
                depth = message["tick"]
                self.ask = depth["asks"][0][0]
                self.askDepth = depth["asks"][0][1]
                self.bid = depth["bids"][0][0]
                self.bidDepth = depth["bids"][0][1]
                # check_arbitrage("htx")
                # print(f"Best Bid: {self.bid}, Best Ask: {self.ask}")

        self.ws = start_websocket(url="wss://api.huobi.pro/ws", on_message=on_message, on_open=on_open, on_close=on_close)

