# legacy 兼容导入
# 这些模块已迁移到 core.strategy，这里保留为向后兼容
import warnings
warnings.warn("core.strategies 已废弃，请使用 core.strategy", DeprecationWarning, stacklevel=2)

from core.strategy.bollinger_strategy import BollingerStrategy
from core.strategy.ema_rsi_strategy import EMARsiStrategy
from core.strategy.ema_rsi_optimized import EMARsiOptimizedStrategy
from core.strategy.livermore_strategy import LivermoreStrategy
from core.strategy.macd_strategy import MACDStrategy
from core.strategy.multi_strategy import MultiStrategyEngine

# 旧版策略入口
from core.strategy.livermore import LivermoreStage
from core.strategy.engine import StrategyEngine
