// 技术分析服务
class TechnicalAnalysisService {
  constructor() {
    this.symbolData = new Map(); // 存储不同交易对和时间间隔的K线数据
    this.indicatorsCache = new Map(); // 存储计算的指标缓存
  }

  // 清除指定交易对和时间间隔的缓存数据
  clearSymbolData(symbol, interval) {
    const key = `${symbol}-${interval}`;
    if (this.symbolData.has(key)) {
      this.symbolData.delete(key);
      this.indicatorsCache.delete(key);
      console.log(`已清除缓存: ${key}`);
    }
  }

  // 添加K线数据
  addKlineData(symbol, interval, kline) {
    const key = `${symbol}-${interval}`;
    if (!this.symbolData.has(key)) {
      this.symbolData.set(key, []);
    }
    const data = this.symbolData.get(key);
    data.push(kline);
    // 保持数据量在合理范围
    if (data.length > 200) {
      this.symbolData.set(key, data.slice(-200));
    }

  }

  // 计算技术指标
  calculateIndicators(symbol, interval, klineData) {
    const key = `${symbol}-${interval}`;
    const data = klineData;
    if (!data || data.length < 5) {
      // 数据不足，无法计算指标
      return
    }

    // 计算简单移动平均线 (SMA)
    const sma5 = this.calculateSMA(data, 5)
    const sma10 = this.calculateSMA(data, 10)
    const sma20 = this.calculateSMA(data, 20)

    // 计算相对强弱指数 (RSI)
    const rsi14 = this.calculateRSI(data, 14)

    // 计算布林带 (BB)
    const bollingerBands = this.calculateBollingerBands(data, 20, 2)

    // 计算移动平均线收敛发散 (MACD)
    const macd = this.calculateMACD(data, 12, 26, 9)

    // 检测异常波动
    const volatilityAlert = this.detectVolatility(data)

    // 存储计算的指标
    this.indicatorsCache.set(key, {
      sma: {
        5: sma5,
        10: sma10,
        20: sma20
      },
      rsi: {
        14: rsi14
      },
      bollingerBands,
      macd,
      volatilityAlert
    })

    console.log(`计算了${symbol}_${interval}的技术指标`)
  }

  // 获取技术指标
  getIndicators(symbol, interval) {
    const key = `${symbol}-${interval}`;
    const klineData = this.symbolData.get(key) || [];
    if (klineData.length < 10) {
      console.log('K线数据不足，无法计算指标', symbol, interval, klineData.length);
      return this.getDefaultIndicators();
    }
    // 计算并缓存指标
      if (!this.indicatorsCache.has(key)) {
        this.calculateIndicators(symbol, interval, klineData);
      }
      return this.indicatorsCache.get(key) || this.getDefaultIndicators();
  }

  // 计算简单移动平均线
  calculateSMA(data, period) {
    if (data.length < period) return 0

    const slice = data.slice(-period)
    const sum = slice.reduce((acc, item) => acc + parseFloat(item.c), 0)
    return sum / period
  }

  // 计算相对强弱指数
  calculateRSI(data, period) {
    if (data.length < period + 1) return 50

    // 只取需要的部分数据
    const slice = data.slice(-period - 1)

    // 计算上涨和下跌的平均值
    let gains = 0
    let losses = 0

    for (let i = 1; i < slice.length; i++) {
      const change = parseFloat(slice[i].c) - parseFloat(slice[i-1].c)
      if (change > 0) {
        gains += change
      } else {
        losses -= change
      }
    }

    // 计算相对强弱指数
    const avgGain = gains / period
    const avgLoss = losses / period
    const rs = avgGain / avgLoss
    return 100 - (100 / (1 + rs))
  }

  // 计算布林带
  calculateBollingerBands(data, period, stdDev) {
    if (data.length < period) return { middle: 0, upper: 0, lower: 0 }

    const slice = data.slice(-period)
    const sma = this.calculateSMA(data, period)

    // 计算标准差
    const variance = slice.reduce((acc, item) => {
      const diff = parseFloat(item.c) - sma
      return acc + diff * diff
    }, 0) / period
    const standardDeviation = Math.sqrt(variance)

    return {
      middle: sma,
      upper: sma + stdDev * standardDeviation,
      lower: sma - stdDev * standardDeviation
    }
  }

  // 计算MACD
  calculateMACD(data, fastPeriod, slowPeriod, signalPeriod) {
    if (data.length < slowPeriod + signalPeriod) return { macdLine: 0, signalLine: 0, histogram: 0 }

    // 计算快速和慢速EMA
    const fastEma = this.calculateEMA(data, fastPeriod)
    const slowEma = this.calculateEMA(data, slowPeriod)

    // 计算MACD线
    const macdLine = fastEma - slowEma

    // 计算信号线 (MACD的EMA)
    // 为了简化，我们这里直接使用最后几个MACD值来计算信号线
    // 收集最近的MACD线值用于计算信号线
    const macdValues = [];
    for (let i = Math.max(0, data.length - signalPeriod); i < data.length; i++) {
      const fastEma = this.calculateEMA(data.slice(0, i+1), fastPeriod);
      const slowEma = this.calculateEMA(data.slice(0, i+1), slowPeriod);
      macdValues.push({ c: fastEma - slowEma });
    }
    const signalLine = this.calculateEMA(macdValues, signalPeriod);

    // 计算柱状图
    const histogram = macdLine - signalLine

    return {
      macdLine,
      signalLine,
      histogram
    }
  }

  // 计算指数移动平均线
  calculateEMA(data, period) {
    if (data.length < period) return 0

    const slice = data.slice(-period)
    const multiplier = 2 / (period + 1)
    let ema = parseFloat(slice[0].c)

    for (let i = 1; i < slice.length; i++) {
      ema = (parseFloat(slice[i].c) - ema) * multiplier + ema
    }

    return ema
  }

  // 检测异常波动
  detectVolatility(data, threshold = 2.5) {
    if (data.length < 20) return false

    // 计算最近20根K线的收盘价标准差
    const closePrices = data.map(item => parseFloat(item.c))
    const mean = closePrices.reduce((sum, price) => sum + price, 0) / closePrices.length
    const stdDev = Math.sqrt(
      closePrices.reduce((sum, price) => sum + Math.pow(price - mean, 2), 0) / closePrices.length
    )

    // 检查最后一根K线的波动是否超过阈值
    const lastPrice = closePrices[closePrices.length - 1]
    const prevPrice = closePrices[closePrices.length - 2]
    const priceChange = Math.abs(lastPrice - prevPrice)

    return priceChange > threshold * stdDev
  }

  // 获取未来走势预测 (基于简单的指标分析)
  getPricePrediction(symbol, interval) {
    const indicators = this.getIndicators(symbol, interval)
    if (!indicators) return null

    const { sma, rsi, macd, bollingerBands } = indicators
    let prediction = '中性'
    let reasons = []

    // 基于SMA判断趋势
    if (sma[20] > sma[50] && sma[50] > sma[200]) {
      reasons.push('短期、中期和长期移动平均线呈多头排列')
    } else if (sma[20] < sma[50] && sma[50] < sma[200]) {
      reasons.push('短期、中期和长期移动平均线呈空头排列')
    }

    // 基于RSI判断超买超卖
    if (rsi[14] > 70) {
      reasons.push('RSI指标显示超买')
    } else if (rsi[14] < 30) {
      reasons.push('RSI指标显示超卖')
    }

    // 基于MACD判断
    if (macd.macdLine > macd.signalLine && macd.histogram > 0) {
      reasons.push('MACD显示看涨信号')
    } else if (macd.macdLine < macd.signalLine && macd.histogram < 0) {
      reasons.push('MACD显示看跌信号')
    }

    // 基于布林带判断
    const key = `${symbol}-${interval}`;
    const klineData = this.symbolData.get(key) || [];
    if (klineData.length === 0) return false;
    const lastPrice = parseFloat(klineData.slice(-1)[0].c)
    if (lastPrice > bollingerBands.upper) {
      reasons.push('价格突破布林带上轨')
    } else if (lastPrice < bollingerBands.lower) {
      reasons.push('价格突破布林带下轨')
    }

    // 综合判断
    if (reasons.length > 0) {
      const bullishReasons = reasons.filter(r => r.includes('多头') || r.includes('看涨') || r.includes('超卖'))
      const bearishReasons = reasons.filter(r => r.includes('空头') || r.includes('看跌') || r.includes('超买'))

      if (bullishReasons.length > bearishReasons.length) {
        prediction = '看涨'
      } else if (bearishReasons.length > bullishReasons.length) {
        prediction = '看跌'
      }
    }

    return {
      prediction,
      reasons,
      supportLevel: bollingerBands.lower,
      resistanceLevel: bollingerBands.upper
    }
  }
}
// 创建并导出单例实例
export const technicalAnalysisService = new TechnicalAnalysisService();