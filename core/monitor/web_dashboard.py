"""
Web监控面板
"""
import asyncio
import json
from datetime import datetime
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from loguru import logger

from core.monitor.contract_monitor import ContractMonitor


app = FastAPI(title="合约数据监控", version="1.0.0")

# 全局监控器
monitor = ContractMonitor()


# HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>合约数据监控</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e; 
            color: #eee; 
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { 
            text-align: center; 
            margin-bottom: 30px;
            color: #00d4ff;
            font-size: 2em;
        }
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); 
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .card h2 {
            color: #00d4ff;
            margin-bottom: 15px;
            font-size: 1.2em;
            border-bottom: 1px solid #0f3460;
            padding-bottom: 10px;
        }
        .price { font-size: 2.5em; font-weight: bold; }
        .price.up { color: #00ff88; }
        .price.down { color: #ff4444; }
        .change { font-size: 1.2em; margin-left: 10px; }
        .change.up { color: #00ff88; }
        .change.down { color: #ff4444; }
        .stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 15px; }
        .stat { 
            background: #0f3460; 
            padding: 10px; 
            border-radius: 8px;
        }
        .stat-label { color: #888; font-size: 0.9em; }
        .stat-value { color: #fff; font-size: 1.1em; margin-top: 5px; }
        .indicators { margin-top: 15px; }
        .indicator-row { 
            display: flex; 
            justify-content: space-between; 
            padding: 8px 0;
            border-bottom: 1px solid #0f3460;
        }
        .indicator-label { color: #888; }
        .indicator-value { color: #fff; font-weight: bold; }
        .signals { 
            margin-top: 15px; 
            padding: 10px;
            background: #0f3460;
            border-radius: 8px;
        }
        .signal { 
            display: inline-block; 
            padding: 5px 10px; 
            margin: 5px;
            border-radius: 15px;
            font-size: 0.9em;
        }
        .signal.bullish { background: #00ff8822; color: #00ff88; }
        .signal.bearish { background: #ff444422; color: #ff4444; }
        .signal.neutral { background: #88888822; color: #888; }
        .alerts { 
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
        }
        .alerts h2 { color: #ffaa00; }
        .alert-item {
            padding: 10px;
            margin: 10px 0;
            background: #0f3460;
            border-radius: 8px;
            border-left: 4px solid #ffaa00;
        }
        .alert-time { color: #888; font-size: 0.9em; }
        .alert-text { color: #fff; margin-top: 5px; }
        .status-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #0f3460;
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 10px;
        }
        .status-dot.online { background: #00ff88; }
        .status-dot.offline { background: #ff4444; }
        .loading { text-align: center; padding: 50px; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 合约数据监控</h1>
        
        <div class="grid" id="market-grid">
            <div class="loading">加载中...</div>
        </div>
        
        <div class="alerts">
            <h2>🚨 报警记录</h2>
            <div id="alerts-list">
                <div class="loading">暂无报警</div>
            </div>
        </div>
    </div>
    
    <div class="status-bar">
        <div>
            <span class="status-dot online" id="status-dot"></span>
            <span id="status-text">连接中...</span>
        </div>
        <div id="update-time">--</div>
    </div>

    <script>
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        const grid = document.getElementById('market-grid');
        const alertsList = document.getElementById('alerts-list');
        const statusText = document.getElementById('status-text');
        const statusDot = document.getElementById('status-dot');
        const updateTime = document.getElementById('update-time');

        ws.onopen = () => {
            statusText.textContent = '已连接';
            statusDot.className = 'status-dot online';
        };

        ws.onclose = () => {
            statusText.textContent = '已断开';
            statusDot.className = 'status-dot offline';
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateUI(data);
        };

        function updateUI(data) {
            // 更新市场数据
            if (data.snapshots) {
                let html = '';
                for (const [symbol, snap] of Object.entries(data.snapshots)) {
                    const ind = data.indicators?.[symbol];
                    const changeClass = snap.change_24h >= 0 ? 'up' : 'down';
                    const changeSign = snap.change_24h >= 0 ? '+' : '';
                    
                    html += `
                    <div class="card">
                        <h2>${symbol}</h2>
                        <div>
                            <span class="price ${changeClass}">$${formatPrice(snap.price)}</span>
                            <span class="change ${changeClass}">${changeSign}${snap.change_24h.toFixed(2)}%</span>
                        </div>
                        <div class="stats">
                            <div class="stat">
                                <div class="stat-label">24h最高</div>
                                <div class="stat-value">$${formatPrice(snap.high_24h)}</div>
                            </div>
                            <div class="stat">
                                <div class="stat-label">24h最低</div>
                                <div class="stat-value">$${formatPrice(snap.low_24h)}</div>
                            </div>
                            <div class="stat">
                                <div class="stat-label">买一</div>
                                <div class="stat-value">$${formatPrice(snap.bid)}</div>
                            </div>
                            <div class="stat">
                                <div class="stat-label">卖一</div>
                                <div class="stat-value">$${formatPrice(snap.ask)}</div>
                            </div>
                        </div>
                        ${ind ? renderIndicators(ind) : ''}
                        ${ind ? renderSignals(ind, snap) : ''}
                    </div>
                    `;
                }
                grid.innerHTML = html;
            }

            // 更新报警
            if (data.alert_history && data.alert_history.length > 0) {
                let html = '';
                for (const alert of data.alert_history.slice(-5).reverse()) {
                    html += `
                    <div class="alert-item">
                        <div class="alert-time">${alert.timestamp}</div>
                        <div class="alert-text">${alert.rule}</div>
                    </div>
                    `;
                }
                alertsList.innerHTML = html;
            }

            // 更新时间
            updateTime.textContent = `更新时间: ${new Date().toLocaleTimeString()}`;
        }

        function renderIndicators(ind) {
            return `
            <div class="indicators">
                <div class="indicator-row">
                    <span class="indicator-label">EMA20</span>
                    <span class="indicator-value">$${formatPrice(ind.ema_20)}</span>
                </div>
                <div class="indicator-row">
                    <span class="indicator-label">EMA50</span>
                    <span class="indicator-value">$${formatPrice(ind.ema_50)}</span>
                </div>
                <div class="indicator-row">
                    <span class="indicator-label">RSI(14)</span>
                    <span class="indicator-value">${ind.rsi_14.toFixed(1)}</span>
                </div>
                <div class="indicator-row">
                    <span class="indicator-label">MACD</span>
                    <span class="indicator-value">${ind.macd.toFixed(8)}</span>
                </div>
                <div class="indicator-row">
                    <span class="indicator-label">成交量比</span>
                    <span class="indicator-value">${ind.volume_ratio.toFixed(2)}x</span>
                </div>
            </div>
            `;
        }

        function renderSignals(ind, snap) {
            const signals = [];
            
            if (ind.rsi_14 > 70) signals.push({text: 'RSI超买', class: 'bearish'});
            else if (ind.rsi_14 < 30) signals.push({text: 'RSI超卖', class: 'bullish'});
            
            if (snap.price > ind.bb_upper) signals.push({text: '突破布林上轨', class: 'bullish'});
            else if (snap.price < ind.bb_lower) signals.push({text: '跌破布林下轨', class: 'bearish'});
            
            if (ind.macd_hist > 0) signals.push({text: 'MACD金叉', class: 'bullish'});
            else signals.push({text: 'MACD死叉', class: 'bearish'});
            
            if (signals.length === 0) return '';
            
            return `
            <div class="signals">
                ${signals.map(s => `<span class="signal ${s.class}">${s.text}</span>`).join('')}
            </div>
            `;
        }

        function formatPrice(price) {
            if (price < 0.001) return price.toFixed(8);
            if (price < 1) return price.toFixed(6);
            return price.toFixed(4);
        }

        // 定时刷新
        setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send('refresh');
            }
        }, 5000);
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get():
    """返回监控页面"""
    return HTML_TEMPLATE


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接"""
    await websocket.accept()
    
    try:
        while True:
            # 接收消息
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                data = None
            
            # 更新数据
            monitor.update()
            
            # 发送数据
            status = monitor.get_status()
            await websocket.send_json(status)
            
            await asyncio.sleep(5)  # 5秒更新一次
            
    except WebSocketDisconnect:
        logger.info("WebSocket客户端断开")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")


@app.get("/api/status")
async def get_status():
    """获取监控状态API"""
    return monitor.get_status()


@app.get("/api/overview")
async def get_overview():
    """获取市场概览API"""
    return {"overview": monitor.get_market_overview()}


def start_web_monitor(host: str = "0.0.0.0", port: int = 8080):
    """启动Web监控"""
    logger.info(f"启动Web监控: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == '__main__':
    start_web_monitor()