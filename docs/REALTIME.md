# 实时交易引擎

## 启动方式

### 前台运行
```bash
cd ~/quant-trading-system
source venv/bin/activate
python realtime.py
```

### 后台服务（开机自启）
```bash
# 管理命令
./manage_realtime.sh start    # 启动
./manage_realtime.sh stop     # 停止
./manage_realtime.sh restart  # 重启
./manage_realtime.sh status   # 查看状态
./manage_realtime.sh logs     # 查看日志
./manage_realtime.sh unload   # 卸载（取消开机自启）
./manage_realtime.sh load     # 加载（恢复开机自启）
```

## 文件说明
- `realtime.py` - 主程序入口
- `start_realtime.sh` - LaunchAgent启动脚本
- `manage_realtime.sh` - 服务管理脚本
- `~/Library/LaunchAgents/com.quant.realtime.plist` - macOS服务配置
- `logs/launchd_stdout.log` - 标准输出日志
- `logs/launchd_stderr.log` - 错误/运行日志

## 默认配置
- 交易对: DOGEUSDT, PEPEUSDT
- K线周期: 1h
- 策略: 利弗莫尔
- 杠杆: 10x
- 资金: 10U

## 修改参数
编辑 `start_realtime.sh` 中的默认值，然后重启服务：
```bash
./manage_realtime.sh restart
```
