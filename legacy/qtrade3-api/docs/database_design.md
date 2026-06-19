# Binance个人量化交易平台数据库设计文档

## 1. 数据库概述

本系统采用MySQL作为主要的关系型数据库，用于存储用户信息、交易数据、策略配置等持久化数据。同时使用Redis作为缓存数据库，用于存储实时行情数据、临时会话信息等需要高速访问的数据。

## 2. MySQL数据库设计

### 2.1 用户相关表

#### 2.1.1 users表（用户基本信息）

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | 用户ID |
| username | VARCHAR(50) | NOT NULL, UNIQUE | 用户名 |
| email | VARCHAR(100) | NOT NULL, UNIQUE | 邮箱 |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希值 |
| phone | VARCHAR(20) | NULL | 手机号 |
| role | ENUM('user', 'admin') | NOT NULL, DEFAULT 'user' | 用户角色 |
| status | ENUM('active', 'inactive', 'banned') | NOT NULL, DEFAULT 'active' | 账号状态 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| last_login | TIMESTAMP | NULL | 最后登录时间 |
| login_ip | VARCHAR(50) | NULL | 最后登录IP |

#### 2.1.2 user_settings表（用户设置）

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | 设置ID |
| user_id | INT | NOT NULL, FOREIGN KEY | 关联用户ID |
| theme | VARCHAR(20) | DEFAULT 'light' | 界面主题 |
| language | VARCHAR(10) | DEFAULT 'zh-CN' | 界面语言 |
| notification_enabled | BOOLEAN | DEFAULT TRUE | 是否启用通知 |
| two_factor_auth | BOOLEAN | DEFAULT FALSE | 是否启用双因素认证 |
| settings_json | JSON | NULL | 其他设置（JSON格式） |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

#### 2.1.3 api_keys表（用户API密钥）

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | 密钥ID |
| user_id | INT | NOT NULL, FOREIGN KEY | 关联用户ID |
| api_name | VARCHAR(50) | NOT NULL | API名称（用户自定义） |
| api_key | VARCHAR(255) | NOT NULL | 加密存储的API Key |
| api_secret | VARCHAR(255) | NOT NULL | 加密存储的API Secret |
| permissions | JSON | NOT NULL | API权限设置 |
| status | ENUM('active', 'inactive') | NOT NULL, DEFAULT 'active' | 密钥状态 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| last_used | TIMESTAMP | NULL | 最后使用时间 |

### 2.2 交易相关表

#### 2.2.1 trading_pairs表（交易对信息）

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | 交易对ID |
| symbol | VARCHAR(20) | NOT NULL, UNIQUE | 交易对符号（如BTCUSDT） |
| base_asset | VARCHAR(10) | NOT NULL | 基础资产（如BTC） |
| quote_asset | VARCHAR(10) | NOT NULL | 计价资产（如USDT） |
| min_price | DECIMAL(24,8) | NOT NULL | 最小价格变动单位 |
| min_qty | DECIMAL(24,8) | NOT NULL | 最小交易数量 |
| status | ENUM('trading', 'halt', 'break') | NOT NULL, DEFAULT 'trading' | 交易状态 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

#### 2.2.2 kline_data表（K线历史数据）

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO_INCREMENT | 数据ID |
| symbol | VARCHAR(20) | NOT NULL | 交易对符号 |
| interval | VARCHAR(10) | NOT NULL | 时间间隔（1m, 5m, 15m, 1h, 4h, 1d等） |
| open_time | BIGINT | NOT NULL | 开盘时间（毫秒时间戳） |
| open_price | DECIMAL(24,8) | NOT NULL | 开盘价 |
| high_price | DECIMAL(24,8) | NOT NULL | 最高价 |
| low_price | DECIMAL(24,8) | NOT NULL | 最低价 |
| close_price | DECIMAL(24,8) | NOT NULL | 收盘价 |
| volume | DECIMAL(24,8) | NOT NULL | 成交量 |
| close_time | BIGINT | NOT NULL | 收盘时间（毫秒时间戳） |
| quote_asset_volume | DECIMAL(24,8) | NOT NULL | 计价资产成交量 |
| number_of_trades | INT | NOT NULL | 成交笔数 |
| taker_buy_base_asset_volume | DECIMAL(24,8) | NOT NULL | 主动买入成交量 |
| taker_buy_quote_asset_volume | DECIMAL(24,8) | NOT NULL | 主动买入成交额 |

索引：
- INDEX(symbol, interval, open_time)

#### 2.2.3 orders表（用户订单）

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO_INCREMENT | 订单ID |
| user_id | INT | NOT NULL, FOREIGN KEY | 关联用户ID |
| strategy_id | INT | NULL, FOREIGN KEY | 关联策略ID（如果是策略触发） |
| exchange_order_id | VARCHAR(50) | NULL | 交易所订单ID |
| symbol | VARCHAR(20) | NOT NULL | 交易对符号 |
| side | ENUM('BUY', 'SELL') | NOT NULL | 买卖方向 |
| type | ENUM('LIMIT', 'MARKET', 'STOP_LOSS', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT', 'TAKE_PROFIT_LIMIT') | NOT NULL | 订单类型 |
| time_in_force | ENUM('GTC', 'IOC', 'FOK') | NULL | 有效方式 |
| quantity | DECIMAL(24,8) | NOT NULL | 数量 |
| price | DECIMAL(24,8) | NULL | 价格（市价单为NULL） |
| stop_price | DECIMAL(24,8) | NULL | 触发价（止损/止盈订单） |
| status | ENUM('NEW', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED', 'REJECTED', 'EXPIRED') | NOT NULL | 订单状态 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| executed_qty | DECIMAL(24,8) | DEFAULT 0 | 已成交数量 |
| cummulative_quote_qty | DECIMAL(24,8) | DEFAULT 0 | 累计成交金额 |
| avg_price | DECIMAL(24,8) | NULL | 成交均价 |
| commission | DECIMAL(24,8) | DEFAULT 0 | 手续费 |
| commission_asset | VARCHAR(10) | NULL | 手续费资产 |

索引：
- INDEX(user_id, symbol, created_at)
- INDEX(strategy_id)
- INDEX(exchange_order_id)

#### 2.2.4 trades表（成交记录）

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO_INCREMENT | 成交ID |
| order_id | BIGINT | NOT NULL, FOREIGN KEY | 关联订单ID |
| user_id | INT | NOT NULL, FOREIGN KEY | 关联用户ID |
| exchange_trade_id | VARCHAR(50) | NULL | 交易所成交ID |
| symbol | VARCHAR(20) | NOT NULL | 交易对符号 |
| price | DECIMAL(24,8) | NOT NULL | 成交价格 |
| quantity | DECIMAL(24,8) | NOT NULL | 成交数量 |
| commission | DECIMAL(24,8) | NOT NULL | 手续费 |
| commission_asset | VARCHAR(10) | NOT NULL | 手续费资产 |
| trade_time | TIMESTAMP | NOT NULL | 成交时间 |
| is_buyer | BOOLEAN | NOT NULL | 是否为买方 |
| is_maker | BOOLEAN | NOT NULL | 是否为挂单方 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |

索引：
- INDEX(user_id, symbol, trade_time)
- INDEX(order_id)

### 2.3 策略相关表

#### 2.3.1 strategies表（交易策略）

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | 策略ID |
| user_id | INT | NOT NULL, FOREIGN KEY | 关联用户ID |
| name | VARCHAR(100) | NOT NULL | 策略名称 |
| description | TEXT | NULL | 策略描述 |
| symbol | VARCHAR(20) | NOT NULL | 交易对符号 |
| interval | VARCHAR(10) | NOT NULL | 时间间隔 |
| status | ENUM('active', 'inactive', 'testing', 'error') | NOT NULL, DEFAULT 'inactive' | 策略状态 |
| type | ENUM('predefined', 'custom') | NOT NULL | 策略类型 |
| code | TEXT | NULL | 策略代码（自定义策略） |
| parameters | JSON | NOT NULL | 策略参数（JSON格式） |
| risk_limit | JSON | NOT NULL | 风险控制参数 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| last_run | TIMESTAMP | NULL | 最后运行时间 |
| version | INT | NOT NULL, DEFAULT 1 | 策略版本号 |

#### 2.3.2 strategy_logs表（策略执行日志）

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO_INCREMENT | 日志ID |
| strategy_id | INT | NOT NULL, FOREIGN KEY | 关联策略ID |
| user_id | INT | NOT NULL, FOREIGN KEY | 关联用户ID |
| log_level | ENUM('info', 'warning', 'error', 'debug') | NOT NULL | 日志级别 |
| message | TEXT | NOT NULL | 日志消息 |
| details | JSON | NULL | 详细信息（JSON格式） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

索引：
- INDEX(strategy_id, created_at)
- INDEX(user_id, log_level, created_at)

#### 2.3.3 strategy_performance表（策略性能）

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | 记录ID |
| strategy_id | INT | NOT NULL, FOREIGN KEY | 关联策略ID |
| start_time | TIMESTAMP | NOT NULL | 统计开始时间 |
| end_time | TIMESTAMP | NOT NULL | 统计结束时间 |
| total_trades | INT | NOT NULL, DEFAULT 0 | 总交易次数 |
| winning_trades | INT | NOT NULL, DEFAULT 0 | 盈利交易次数 |
| losing_trades | INT | NOT NULL, DEFAULT 0 | 亏损交易次数 |
| total_profit | DECIMAL(24,8) | NOT NULL, DEFAULT 0 | 总盈利（计价货币） |
| total_loss | DECIMAL(24,8) | NOT NULL, DEFAULT 0 | 总亏损（计价货币） |
| max_drawdown | DECIMAL(24,8) | NOT NULL, DEFAULT 0 | 最大回撤 |
| sharpe_ratio | DECIMAL(10,4) | NULL | 夏普比率 |
| win_rate | DECIMAL(5,2) | NULL | 胜率（百分比） |
| profit_factor | DECIMAL(10,4) | NULL | 盈亏比 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

### 2.4 系统相关表

#### 2.4.1 system_logs表（系统日志）

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO_INCREMENT | 日志ID |
| log_level | ENUM('info', 'warning', 'error', 'critical') | NOT NULL | 日志级别 |
| component | VARCHAR(50) | NOT NULL | 系统组件 |
| message | TEXT | NOT NULL | 日志消息 |
| details | JSON | NULL | 详细信息（JSON格式） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

索引：
- INDEX(log_level, component, created_at)

#### 2.4.2 user_activities表（用户活动日志）

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO_INCREMENT | 活动ID |
| user_id | INT | NOT NULL, FOREIGN KEY | 关联用户ID |
| activity_type | VARCHAR(50) | NOT NULL | 活动类型 |
| description | TEXT | NOT NULL | 活动描述 |
| ip_address | VARCHAR(50) | NULL | IP地址 |
| user_agent | VARCHAR(255) | NULL | 用户代理 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

索引：
- INDEX(user_id, activity_type, created_at)

#### 2.4.3 system_configs表（系统配置）

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | 配置ID |
| config_key | VARCHAR(100) | NOT NULL, UNIQUE | 配置键 |
| config_value | TEXT | NOT NULL | 配置值 |
| description | VARCHAR(255) | NULL | 配置描述 |
| updated_by | INT | NULL, FOREIGN KEY | 更新用户ID |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

## 3. Redis数据库设计

Redis将主要用于以下几个方面：
1. 实时行情数据缓存
2. 用户会话管理
3. 任务队列
4. 实时通知

### 3.1 键值设计

#### 3.1.1 实时行情数据

- `market:ticker:{symbol}` - 存储交易对的最新行情数据（Hash类型）
  - fields: last_price, bid_price, ask_price, 24h_high, 24h_low, 24h_volume, etc.

- `market:kline:{symbol}:{interval}` - 存储最近的K线数据（Sorted Set类型）
  - score: timestamp
  - member: JSON格式的K线数据

- `market:depth:{symbol}` - 存储市场深度数据（Hash类型）
  - fields: bids, asks (JSON格式)

- `market:trades:{symbol}` - 存储最近的成交记录（List类型）
  - 每个元素为JSON格式的成交记录

#### 3.1.2 用户会话管理

- `session:{session_id}` - 存储用户会话信息（Hash类型）
  - fields: user_id, username, login_time, expire_time, etc.

- `user:online:{user_id}` - 用户在线状态（String类型）
  - value: session_id

#### 3.1.3 任务队列

- `queue:strategy_execution` - 策略执行队列（List类型）
  - 每个元素为JSON格式的策略执行任务

- `queue:data_processing` - 数据处理队列（List类型）
  - 每个元素为JSON格式的数据处理任务

#### 3.1.4 实时通知

- `notifications:{user_id}` - 用户通知队列（List类型）
  - 每个元素为JSON格式的通知消息

- `alerts:{user_id}` - 用户告警（Sorted Set类型）
  - score: 优先级
  - member: JSON格式的告警信息

#### 3.1.5 限流与安全

- `rate_limit:api:{user_id}` - API调用频率限制（Hash类型）
  - fields: 各API端点的调用次数

- `banned_ips` - 被禁止的IP地址（Set类型）
  - members: IP地址

### 3.2 过期策略

- 实时行情数据：根据数据类型设置不同的过期时间
  - 最新行情（ticker）：60秒
  - K线数据：根据时间间隔设置（1分钟K线保留2小时，1小时K线保留2天等）
  - 市场深度：30秒
  - 最近成交：10分钟

- 用户会话：根据系统设置的会话有效期（默认24小时）

- 任务队列：任务完成后自动移除

- 实时通知：读取后或7天后自动过期

- 限流数据：根据限流窗口设置（如1分钟、1小时等）

## 4. 数据库关系图

```
users 1 --- * user_settings
users 1 --- * api_keys
users 1 --- * orders
users 1 --- * strategies
strategies 1 --- * strategy_logs
strategies 1 --- * strategy_performance
orders 1 --- * trades
```

## 5. 数据库优化策略

### 5.1 MySQL优化

1. 索引优化
   - 为频繁查询的字段创建适当的索引
   - 使用复合索引优化多字段查询
   - 定期分析和优化索引

2. 分区策略
   - 对大表（如kline_data, trades）按时间范围进行分区
   - 根据访问模式优化分区策略

3. 查询优化
   - 使用预编译语句
   - 优化JOIN操作
   - 限制返回结果集大小

4. 配置优化
   - 调整缓冲池大小
   - 优化事务隔离级别
   - 配置适当的连接池

### 5.2 Redis优化

1. 内存管理
   - 设置合理的maxmemory值
   - 配置适当的淘汰策略（如volatile-lru）

2. 持久化策略
   - 配置RDB和AOF持久化
   - 设置合理的持久化频率

3. 连接池管理
   - 配置适当的连接池大小
   - 设置连接超时时间

4. 数据结构优化
   - 选择合适的数据结构
   - 压缩大体积数据

## 6. 数据安全策略

1. 数据加密
   - 敏感数据（如API密钥）使用AES-256加密存储
   - 传输过程中使用TLS/SSL加密

2. 访问控制
   - 实施基于角色的访问控制（RBAC）
   - 最小权限原则

3. 数据备份
   - 定期全量备份
   - 实时增量备份
   - 备份数据加密存储

4. 审计日志
   - 记录所有数据修改操作
   - 记录敏感数据访问

## 7. 扩展性考虑

1. 分库分表
   - 为未来用户增长预留分库分表方案
   - 设计合理的分片键

2. 读写分离
   - 主从复制架构
   - 读操作分发到从库

3. 缓存策略
   - 多级缓存设计
   - 缓存预热和更新策略

4. 微服务拆分
   - 按业务领域划分数据库
   - 服务间数据一致性保障