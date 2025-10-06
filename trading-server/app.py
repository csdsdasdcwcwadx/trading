from flask import Flask, request, jsonify
from util import init_clients, clients
import logging
import os
import asyncio

app = Flask(__name__)

# 首頁
@app.route("/")
def index():
    return "hello world"

# POST API 範例：回傳前端送的資料
@app.route("/api/echo", methods=["POST"])
def echo():
    content = request.json
    return jsonify({"you_sent": content})

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('trading.log', encoding='utf-8')
            ]
        )
        logger = logging.getLogger(__name__)

        init_clients()
        for name, client in clients.items():
            client.start_ws()

    app.run(debug=True)
