import pino from 'pino'

const isDevelopment = process.env.NODE_ENV === 'development'

// Pino logger設定
// Note: pino-prettyはNext.js Turbopackと互換性がないため、
// 開発環境でもJSON形式を使用（ログレベルでdebugを許可）
export const logger = pino({
  // 本番環境ではinfoレベル以上、開発環境ではdebug
  level: process.env.LOG_LEVEL || (isDevelopment ? 'debug' : 'info'),
  // ベースとなる共通フィールド
  base: {
    service: 'pbap-user-app',
    version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
    env: process.env.NODE_ENV
  },
  // タイムスタンプを有効化
  timestamp: pino.stdTimeFunctions.isoTime
})

// 子loggerを作成するヘルパー関数
export const createChildLogger = (component: string, additionalContext?: Record<string, unknown>) => {
  return logger.child({
    component,
    ...additionalContext
  })
}

// リクエストID生成
export const generateRequestId = () => {
  return `req_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
}