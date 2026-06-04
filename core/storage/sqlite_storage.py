"""
SQLite数据存储模块
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from loguru import logger
import os


class SQLiteStorage:
    """SQLite数据存储"""
    
    def __init__(self, db_path: str = "data/trading.db"):
        """初始化存储
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        logger.info(f"SQLite存储初始化完成: {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 行情数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                bid REAL,
                ask REAL,
                high_24h REAL,
                low_24h REAL,
                volume_24h REAL,
                change_24h REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timestamp)
            )
        ''')
        
        # K线数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS klines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                UNIQUE(symbol, timeframe, timestamp)
            )
        ''')
        
        # 技术指标表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                ema_20 REAL,
                ema_50 REAL,
                ema_200 REAL,
                rsi_14 REAL,
                macd REAL,
                macd_signal REAL,
                macd_hist REAL,
                bb_upper REAL,
                bb_middle REAL,
                bb_lower REAL,
                volume_ma_20 REAL,
                volume_ratio REAL,
                UNIQUE(symbol, timeframe, timestamp)
            )
        ''')
        
        # 交易信号表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                price REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                confidence REAL,
                reason TEXT,
                executed BOOLEAN DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 交易记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                amount REAL NOT NULL,
                leverage INTEGER DEFAULT 1,
                pnl REAL,
                pnl_pct REAL,
                entry_time DATETIME NOT NULL,
                exit_time DATETIME,
                duration TEXT,
                reason TEXT,
                status TEXT DEFAULT 'open',
                stop_loss REAL DEFAULT 0,
                take_profit REAL DEFAULT 0,
                highest_pnl_pct REAL DEFAULT 0
            )
        ''')
        
        # 账户快照表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                balance REAL NOT NULL,
                total_pnl REAL DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                open_positions INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 持仓表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                side TEXT NOT NULL,
                amount REAL NOT NULL,
                entry_price REAL NOT NULL,
                leverage INTEGER DEFAULT 1,
                highest_pnl_pct REAL DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 报警记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                condition TEXT NOT NULL,
                threshold REAL,
                current_value REAL,
                message TEXT,
                triggered BOOLEAN DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickers_symbol ON tickers(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickers_timestamp ON tickers(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_klines_symbol ON klines(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_klines_timestamp ON klines(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON alerts(symbol)')
        
        conn.commit()
        conn.close()
        
        logger.info("数据库表初始化完成")
    
    # ==================== 行情数据 ====================
    
    def save_ticker(self, symbol: str, data: Dict):
        """保存行情数据"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO tickers 
            (symbol, price, bid, ask, high_24h, low_24h, volume_24h, change_24h, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol,
            data.get('last', 0),
            data.get('bid', 0),
            data.get('ask', 0),
            data.get('high', 0),
            data.get('low', 0),
            data.get('volume', 0),
            data.get('change', 0),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_latest_ticker(self, symbol: str) -> Optional[Dict]:
        """获取最新行情"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM tickers 
            WHERE symbol = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (symbol,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_ticker_history(self, symbol: str, hours: int = 24) -> List[Dict]:
        """获取历史行情"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT * FROM tickers 
            WHERE symbol = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', (symbol, since))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ==================== K线数据 ====================
    
    def save_klines(self, symbol: str, timeframe: str, klines: List):
        """保存K线数据"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for kline in klines:
            timestamp = datetime.fromtimestamp(kline[0] / 1000).isoformat()
            
            cursor.execute('''
                INSERT OR REPLACE INTO klines 
                (symbol, timeframe, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol, timeframe, timestamp,
                kline[1], kline[2], kline[3], kline[4], kline[5]
            ))
        
        conn.commit()
        conn.close()
    
    def get_klines(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List:
        """获取K线数据"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, open, high, low, close, volume 
            FROM klines 
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (symbol, timeframe, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        # 转换为列表格式
        return [[
            int(datetime.fromisoformat(row[0]).timestamp() * 1000),
            row[1], row[2], row[3], row[4], row[5]
        ] for row in reversed(rows)]
    
    # ==================== 技术指标 ====================
    
    def save_indicators(self, symbol: str, timeframe: str, indicators: Dict):
        """保存技术指标"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO indicators 
            (symbol, timeframe, timestamp, ema_20, ema_50, ema_200, rsi_14,
             macd, macd_signal, macd_hist, bb_upper, bb_middle, bb_lower,
             volume_ma_20, volume_ratio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol, timeframe, datetime.now().isoformat(),
            indicators.get('ema_20'),
            indicators.get('ema_50'),
            indicators.get('ema_200'),
            indicators.get('rsi_14'),
            indicators.get('macd'),
            indicators.get('macd_signal'),
            indicators.get('macd_hist'),
            indicators.get('bb_upper'),
            indicators.get('bb_middle'),
            indicators.get('bb_lower'),
            indicators.get('volume_ma_20'),
            indicators.get('volume_ratio')
        ))
        
        conn.commit()
        conn.close()
    
    def get_latest_indicators(self, symbol: str, timeframe: str = '1h') -> Optional[Dict]:
        """获取最新技术指标"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM indicators 
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (symbol, timeframe))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    # ==================== 交易信号 ====================
    
    def save_signal(self, signal: Dict):
        """保存交易信号"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO signals 
            (symbol, signal_type, price, stop_loss, take_profit, confidence, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal.get('symbol'),
            signal.get('signal_type'),
            signal.get('price'),
            signal.get('stop_loss'),
            signal.get('take_profit'),
            signal.get('confidence'),
            signal.get('reason')
        ))
        
        conn.commit()
        conn.close()
    
    def get_signals(self, symbol: str = None, limit: int = 50) -> List[Dict]:
        """获取交易信号"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('''
                SELECT * FROM signals 
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (symbol, limit))
        else:
            cursor.execute('''
                SELECT * FROM signals 
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ==================== 交易记录 ====================
    
    def save_trade(self, trade: Dict):
        """保存交易记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades 
            (symbol, side, entry_price, exit_price, amount, leverage, 
             pnl, pnl_pct, entry_time, exit_time, duration, reason, status,
             stop_loss, take_profit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.get('symbol'),
            trade.get('side'),
            trade.get('entry_price'),
            trade.get('exit_price'),
            trade.get('amount'),
            trade.get('leverage', 1),
            trade.get('pnl'),
            trade.get('pnl_pct'),
            trade.get('entry_time'),
            trade.get('exit_time'),
            trade.get('duration'),
            trade.get('reason'),
            trade.get('status', 'closed'),
            trade.get('stop_loss', 0),
            trade.get('take_profit', 0)
        ))
        
        conn.commit()
        conn.close()
    
    def update_trade(self, trade_id: int, updates: Dict):
        """更新交易记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [trade_id]
        
        cursor.execute(f'''
            UPDATE trades SET {set_clause} WHERE id = ?
        ''', values)
        
        conn.commit()
        conn.close()
    
    def update_trade_by_symbol_time(self, symbol: str, entry_time: str, updates: Dict):
        """根据币种和开仓时间更新交易记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [symbol, entry_time]
        
        cursor.execute(f'''
            UPDATE trades SET {set_clause} 
            WHERE symbol = ? AND entry_time = ? AND status = 'open'
        ''', values)
        
        conn.commit()
        conn.close()
    
    def get_trades(self, symbol: str = None, status: str = None, limit: int = 100) -> List[Dict]:
        """获取交易记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        cursor.execute(f'''
            SELECT * FROM trades 
            WHERE {where_clause}
            ORDER BY entry_time DESC
            LIMIT ?
        ''', params + [limit])
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_open_trades(self) -> List[Dict]:
        """获取未平仓交易"""
        return self.get_trades(status='open')
    
    # ==================== 持仓管理 ====================
    
    def save_position(self, symbol: str, side: str, amount: float, 
                      entry_price: float, leverage: int = 1, highest_pnl_pct: float = 0):
        """保存持仓到positions表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        from datetime import datetime
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO positions 
            (symbol, side, amount, entry_price, leverage, highest_pnl_pct, timestamp, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, side, amount, entry_price, leverage, highest_pnl_pct, now, now, now))
        
        conn.commit()
        conn.close()
    
    def remove_position(self, symbol: str):
        """从positions表删除持仓"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM positions WHERE symbol = ?', (symbol,))
        
        conn.commit()
        conn.close()
    
    def update_position_pnl(self, symbol: str, highest_pnl_pct: float):
        """更新持仓的highest_pnl_pct"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        from datetime import datetime
        cursor.execute('''
            UPDATE positions 
            SET highest_pnl_pct = ?, updated_at = ?
            WHERE symbol = ?
        ''', (highest_pnl_pct, datetime.now().isoformat(), symbol))
        
        conn.commit()
        conn.close()
    
    def get_open_positions(self) -> List[Dict]:
        """获取所有持仓"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM positions ORDER BY timestamp DESC')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_last_open_time(self, symbol: str) -> str:
        """获取指定币种最近一次开仓时间"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT entry_time FROM trades 
            WHERE symbol = ? AND status = 'open'
            ORDER BY entry_time DESC 
            LIMIT 1
        ''', (symbol,))
        
        row = cursor.fetchone()
        conn.close()
        
        return row['entry_time'] if row else None
    
    def get_open_trade_count(self, symbol: str) -> int:
        """获取指定币种的持仓笔数"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as cnt FROM trades 
            WHERE symbol = ? AND status = 'open'
        ''', (symbol,))
        
        row = cursor.fetchone()
        conn.close()
        
        return row['cnt'] if row else 0
    
    # ==================== 账户快照 ====================
    
    def save_account_snapshot(self, account: Dict):
        """保存账户快照"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO account_snapshots 
            (balance, total_pnl, total_trades, winning_trades, losing_trades, open_positions, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            account.get('balance'),
            account.get('total_pnl'),
            account.get('total_trades'),
            account.get('winning_trades'),
            account.get('losing_trades'),
            account.get('open_positions', 0),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_latest_snapshot(self) -> Optional[Dict]:
        """获取最新账户快照"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM account_snapshots 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_snapshot_history(self, days: int = 30) -> List[Dict]:
        """获取账户快照历史"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT * FROM account_snapshots 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        ''', (since,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ==================== 报警记录 ====================
    
    def save_alert(self, alert: Dict):
        """保存报警记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts 
            (symbol, alert_type, condition, threshold, current_value, message, triggered)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.get('symbol'),
            alert.get('alert_type'),
            alert.get('condition'),
            alert.get('threshold'),
            alert.get('current_value'),
            alert.get('message'),
            alert.get('triggered', 1)
        ))
        
        conn.commit()
        conn.close()
    
    def get_alerts(self, symbol: str = None, limit: int = 50) -> List[Dict]:
        """获取报警记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('''
                SELECT * FROM alerts 
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (symbol, limit))
        else:
            cursor.execute('''
                SELECT * FROM alerts 
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ==================== 统计查询 ====================
    
    def get_trade_statistics(self, symbol: str = None) -> Dict:
        """获取交易统计"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as max_win,
                    MIN(pnl) as max_loss,
                    AVG(pnl_pct) as avg_pnl_pct
                FROM trades 
                WHERE symbol = ? AND status = 'closed'
            ''', (symbol,))
        else:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as max_win,
                    MIN(pnl) as max_loss,
                    AVG(pnl_pct) as avg_pnl_pct
                FROM trades 
                WHERE status = 'closed'
            ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            stats = dict(row)
            stats['win_rate'] = (stats['winning_trades'] / max(stats['total_trades'], 1)) * 100
            return stats
        return {}
    
    def get_daily_pnl(self, days: int = 30) -> List[Dict]:
        """获取每日盈亏"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT 
                DATE(exit_time) as date,
                SUM(pnl) as daily_pnl,
                COUNT(*) as trades
            FROM trades 
            WHERE status = 'closed' AND exit_time >= ?
            GROUP BY DATE(exit_time)
            ORDER BY date ASC
        ''', (since,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ==================== 数据迁移 ====================
    
    def migrate_from_json(self, json_path: str):
        """从JSON文件迁移数据"""
        if not os.path.exists(json_path):
            logger.warning(f"JSON文件不存在: {json_path}")
            return
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # 迁移账户数据
            if 'account' in data:
                account = data['account']
                self.save_account_snapshot(account)
                logger.info(f"迁移账户数据: 余额={account.get('balance')}")
            
            # 迁移交易记录
            if 'trades' in data:
                for trade in data['trades']:
                    self.save_trade({
                        'symbol': trade.get('symbol'),
                        'side': trade.get('side'),
                        'entry_price': trade.get('entry_price'),
                        'exit_price': trade.get('exit_price'),
                        'amount': trade.get('amount'),
                        'pnl': trade.get('pnl'),
                        'pnl_pct': trade.get('pnl_pct'),
                        'entry_time': trade.get('entry_time'),
                        'exit_time': trade.get('exit_time'),
                        'duration': trade.get('duration'),
                        'reason': trade.get('reason'),
                        'status': 'closed'
                    })
                logger.info(f"迁移交易记录: {len(data['trades'])} 笔")
            
            logger.info("JSON数据迁移完成")
            
        except Exception as e:
            logger.error(f"JSON数据迁移失败: {e}")
    
    # ==================== 工具方法 ====================
    
    def get_database_info(self) -> Dict:
        """获取数据库信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        tables = ['tickers', 'klines', 'indicators', 'signals', 'trades', 'account_snapshots', 'alerts']
        info = {}
        
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            info[table] = count
        
        conn.close()
        
        # 数据库文件大小
        if os.path.exists(self.db_path):
            size_bytes = os.path.getsize(self.db_path)
            if size_bytes > 1024 * 1024:
                info['db_size'] = f"{size_bytes / 1024 / 1024:.2f} MB"
            else:
                info['db_size'] = f"{size_bytes / 1024:.2f} KB"
        
        return info
    
    def cleanup_old_data(self, days: int = 90):
        """清理旧数据"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        # 清理旧的行情数据
        cursor.execute('DELETE FROM tickers WHERE timestamp < ?', (since,))
        deleted_tickers = cursor.rowcount
        
        # 清理旧的K线数据
        cursor.execute('DELETE FROM klines WHERE timestamp < ?', (since,))
        deleted_klines = cursor.rowcount
        
        # 清理旧的指标数据
        cursor.execute('DELETE FROM indicators WHERE timestamp < ?', (since,))
        deleted_indicators = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"清理旧数据: tickers={deleted_tickers}, klines={deleted_klines}, indicators={deleted_indicators}")


# 使用示例
if __name__ == '__main__':
    storage = SQLiteStorage()
    
    # 获取数据库信息
    info = storage.get_database_info()
    print("数据库信息:")
    for table, count in info.items():
        print(f"  {table}: {count}")
    
    # 迁移JSON数据
    json_path = "data/simulation_history.json"
    if os.path.exists(json_path):
        storage.migrate_from_json(json_path)