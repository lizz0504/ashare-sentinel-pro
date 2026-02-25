/**
 * 市场时间相关工具函数
 */

/**
 * 判断当前是否是开盘时间
 * A股交易时间：周一至周五 9:30-11:30, 13:00-15:00
 */
export function isMarketOpen(): boolean {
  const now = new Date()
  const day = now.getDay()

  // 周末不开盘
  if (day === 0 || day === 6) {
    return false
  }

  const hour = now.getHours()
  const minute = now.getMinutes()
  const time = hour * 60 + minute

  // 上午：9:30-11:30 (570-690)
  const morningStart = 9 * 60 + 30  // 570
  const morningEnd = 11 * 60 + 30   // 690

  // 下午：13:00-15:00 (780-900)
  const afternoonStart = 13 * 60    // 780
  const afternoonEnd = 15 * 60      // 900

  return (time >= morningStart && time < morningEnd) ||
         (time >= afternoonStart && time < afternoonEnd)
}

/**
 * 判断缓存是否有效
 * @param cacheTime 缓存时间戳
 * @param maxAge 最大有效时间（毫秒），默认5分钟
 */
export function isCacheValid(cacheTime: number | null, maxAge: number = 5 * 60 * 1000): boolean {
  if (!cacheTime) return false
  return Date.now() - cacheTime < maxAge
}

/**
 * 获取距离开盘/收盘的时间描述
 */
export function getMarketTimeStatus(): string {
  if (isMarketOpen()) {
    return "交易中"
  }

  const now = new Date()
  const day = now.getDay()

  // 周末
  if (day === 0 || day === 6) {
    return "周末休市"
  }

  const hour = now.getHours()
  const minute = now.getMinutes()
  const time = hour * 60 + minute

  // 上午开盘前
  const morningStart = 9 * 60 + 30  // 570
  if (time < morningStart) {
    return "开盘前"
  }

  // 上午休市
  const morningEnd = 11 * 60 + 30   // 690
  const afternoonStart = 13 * 60    // 780
  if (time >= morningEnd && time < afternoonStart) {
    return "午间休市"
  }

  // 下午收盘后
  return "收盘后"
}
