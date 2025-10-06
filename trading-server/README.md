# Poetry 使用方法

## 創建新專案
```poetry init```

## 安裝 pyproject.toml 裡的依賴
```poetry install```

## 安裝新套件並更新 pyproject.toml
```poetry add <package>```

## 在專案虛擬環境中執行 Python
```poetry run python app.py```

## 顯示專案虛擬環境路徑
```poetry env info --path```

## 更新依賴至最新版本（符合版本限制）
```poetry update```

## VScode 進入 poetry 專案內容
1. 找出 Poetry 虛擬環境路徑 poetry env info --path
2. 打開命令列（Ctrl+Shift+P / Cmd+Shift+P）
3. 搜尋並選擇 Python: Select Interpreter
4. 選剛剛 poetry env info --path 顯示的路徑填進去 "Enter interpreter path"

# 交易所格式 (example)
``` python
    class MEXC:
        def __init__(self):
            data = config["MEXC"]
            self.ws = None

            self.__API_Key = data["API_Key"]
            self.__Secret_Key = data["Secret_Key"]
            self.currency = default_currency
            self.__base_url = "https://api.mexc.com"
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
                        f"spot@public.limit.depth.v3.api.pb@{self.currency.upper()}{stable.upper()}@5"
                    ]
                }
                ws.send(json.dumps(subscribe_msg))

            def on_message(ws, msg):
                if isinstance(msg, str):
                    return

                wrapper = PushDataV3ApiWrapper_pb2.PushDataV3ApiWrapper()
                wrapper.ParseFromString(msg)
                best_ask = wrapper.publicLimitDepths.asks[0]
                best_bid = wrapper.publicLimitDepths.bids[0]

                self.ask = float(best_ask.price)
                self.askDepth = float(best_ask.quantity)
                self.bid = float(best_bid.price)
                self.bidDepth = float(best_bid.quantity)

                check_arbitrage('mexc')
                # print(f"Best Bid: {self.bid}, Best Ask: {self.ask}")

            self.ws = start_websocket(
                url="wss://wbs-api.mexc.com/ws",
                on_message=on_message,
                on_open=on_open
            )

        async def order(self, action: str, amount: str, price = None):
            params = { # MEXC 只能使用限價單
                "symbol": f"{self.currency.upper()}{stable.upper()}",
                "side": action.upper(),
                "type": 'limit'.upper(),
                "quantity": amount,
            }

            if not price == None:
                params["price"] = price
                params["timeInForce"] = "GTC"

            response = self.__sendRequest("POST", "/api/v3/order", params).json()

            return {
                "isSuccess": bool(response.get('orderId')),
                "response": response,
                "orderID": response['orderId']
                # 若失敗再加一個error type
            }

        async def cancel_order(self, orderId: str):
            response = self.__sendRequest("DELETE", "/api/v3/order", {
                "symbol": f"{self.currency.upper()}{stable.upper()}",
                "orderId": orderId,
            }).json()
            return response.get('status')
        
        async def query_order(self, orderID):
            response = self.__sendRequest("GET", "/api/v3/order", {
                "symbol": f"{self.currency.upper()}{stable.upper()}",
                "orderId": orderID
            }).json()

            # FILLED:交易成功 / NEW:尚未交易 / CANCELED:交易取消
            return {
                "isFilled": response['status'] == 'FILLED',
                "price": "",
                "response": response
            }

        async def account(self):
            response = self.__sendRequest("GET", "/api/v3/account").json()
            return response['balances'] # 顯示所有幣種餘額

        def limitation(self):
            resp = requests.get('/api/v3/exchangeInfo').json()
            return resp

        def withdraw(self, amount):
            params = {
                "coin": self.currency.upper(),
                "network": "ERC20",
                "address": "",
                "amount": amount,
                "remark": ""
            }
            response = self.__sendRequest("POST", "/0/private/Withdraw", params).json()
            
        async def getPrice(self, action: str):
            response = requests.get(f'{self.__base_url}/api/v3/depth?symbol={self.currency.upper()}{stable.upper()}&limit=1').json()
            data = response[f'{action}s'][0]
            return {
                'amount': data[1],
                'price': data[0]
            }

        def __sendRequest(self, method: str, endpoint: str, params: dict = {}):
            params["timestamp"] = int(time.time() * 1000)

            signature = hmac.new(
                self.__Secret_Key.encode("utf-8"),
                urlencode(params, quote_via=quote).encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            params["signature"] = signature

            url = self.__base_url + endpoint
            headers = {
                "X-MEXC-APIKEY": self.__API_Key,
                "Content-Type": "application/json"
            }
            match method.upper():
                case "POST":
                    resp = requests.post(url=url, headers=headers, params=params)
                case "GET":
                    resp = requests.get(url=url, headers=headers, params=params)
                case "DELETE":
                    resp = requests.delete(url=url, headers=headers, params=params)

            return resp

```