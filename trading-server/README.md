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
1. 找出 Poetry 虛擬環境路徑
2. 打開命令列（Ctrl+Shift+P / Cmd+Shift+P
3. 搜尋並選擇 Python: Select Interpreter
4. 選剛剛 poetry env info --path 顯示的路徑填進去 "Enter interpreter path"

# Bitopro 

## Limitation 參數解釋
```json
{
    "pair": "btc_usdt",
    "base": "btc",
    "quote": "usdt",
    "basePrecision": "8", // 代表 BTC 最多可以到 8 位小數
    "quotePrecision": "2", // 下單價格（price）最多只能有 2 位小數，例如 60000.12。
    "minLimitBaseAmount": "0.0001", // 代表限價單至少要買/賣 0.0001 BTC。
    "maxLimitBaseAmount": "100000000", // 上限非常大（幾乎無限制），這裡是 100000000 BTC。
    "minMarketBuyQuoteAmount": "7", // 代表市價買單至少要花 7 USDT 才能下單。
    "orderOpenLimit": "200", // 每個帳號在這個交易對上，最多可以同時掛 200 筆未成交訂單。
    "maintain": false, // 是否在維護中。
    "orderBookQuotePrecision": "2", // 例如報價會顯示到 xx.xx，不會顯示太多小數。
    "orderBookQuoteScaleLevel": "5", // 一般用來控制掛單聚合的粒度（例如以 5 個 tick 為一格顯示）。
    "amountPrecision": "4" // 下單數量最多支援 小數點後 4 位，例如 0.0001 BTC。
}
```

# Binance

## Limitation 參數解數
```json
{
    "symbol": "BTCUSDT",
    "status": "TRADING",
    "baseAsset": "BTC",
    "baseAssetPrecision": 8,
    "quoteAsset": "USDT",
    "quotePrecision": 8,
    "quoteAssetPrecision": 8,
    "baseCommissionPrecision": 8,
    "quoteCommissionPrecision": 8,
}
```