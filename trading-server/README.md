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