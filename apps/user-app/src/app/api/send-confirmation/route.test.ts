import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest } from 'next/server'

// loggerをモック
vi.mock('@/lib/logger', () => ({
  createChildLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
  generateRequestId: () => 'test-request-id',
}))

// nodemailerをモック
const mockSendMail = vi.fn()
vi.mock('nodemailer', () => ({
  default: {
    createTransport: vi.fn(() => ({
      sendMail: mockSendMail,
    })),
  },
}))

// グローバルfetchをモック
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

describe('send-confirmation API', () => {
  const originalEnv = process.env

  beforeEach(() => {
    vi.clearAllMocks()
    // 環境変数をリセット
    process.env = {
      ...originalEnv,
      SMTP_HOST: 'smtp.example.com',
      SMTP_PORT: '587',
      SMTP_USER: 'user@example.com',
      SMTP_PASSWORD: 'password',
      SMTP_FROM: 'noreply@example.com',
      NEXT_PUBLIC_SITE_URL: 'http://localhost:3000',
    }
  })

  afterEach(() => {
    process.env = originalEnv
    vi.resetModules()
  })

  const createMockRequest = (body: object) => {
    return new NextRequest('http://localhost:3000/api/send-confirmation', {
      method: 'POST',
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    })
  }

  const validRequestBody = {
    email: 'test@example.com',
    recipientName: 'Test User',
    taskId: 'task-123',
    applicationNumber: 10001,
    productName: 'Test Product',
    partsCount: 3,
    parts: [
      { assemblyNumber: '1', partName: 'Part A', quantity: 1 },
      { assemblyNumber: '2', partName: 'Part B', quantity: 2 },
    ],
    purchaseDate: '2025-01-01',
    purchaseStore: 'Test Store',
  }

  it('should send email successfully with PDF attachment', async () => {
    // PDF生成のモック
    const mockPdfBuffer = Buffer.from('mock pdf content')
    mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: () => Promise.resolve(mockPdfBuffer),
    })

    // メール送信のモック
    mockSendMail.mockResolvedValueOnce({ messageId: 'msg-123' })

    const { POST } = await import('./route')
    const request = createMockRequest(validRequestBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(mockSendMail).toHaveBeenCalledTimes(1)

    // メールオプションの検証
    const mailOptions = mockSendMail.mock.calls[0][0]
    expect(mailOptions.to).toBe('test@example.com')
    expect(mailOptions.subject).toContain('パーツ申請')
    expect(mailOptions.attachments).toHaveLength(1)
    expect(mailOptions.attachments[0].filename).toContain('10001')
  })

  it('should send email without PDF when PDF generation fails', async () => {
    // PDF生成失敗のモック
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: () => Promise.resolve('PDF generation error'),
    })

    // メール送信のモック
    mockSendMail.mockResolvedValueOnce({ messageId: 'msg-123' })

    const { POST } = await import('./route')
    const request = createMockRequest(validRequestBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(mockSendMail).toHaveBeenCalledTimes(1)

    // 添付ファイルなしで送信されたことを確認
    const mailOptions = mockSendMail.mock.calls[0][0]
    expect(mailOptions.attachments).toHaveLength(0)
  })

  it('should skip email when SMTP is not configured', async () => {
    // SMTP設定を削除
    delete process.env.SMTP_HOST

    const { POST } = await import('./route')
    const request = createMockRequest(validRequestBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(data.skipped).toBe(true)
    expect(mockSendMail).not.toHaveBeenCalled()
  })

  it('should return 500 when email sending fails', async () => {
    // PDF生成のモック
    mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: () => Promise.resolve(Buffer.from('mock pdf')),
    })

    // メール送信失敗のモック
    mockSendMail.mockRejectedValueOnce(new Error('SMTP connection failed'))

    const { POST } = await import('./route')
    const request = createMockRequest(validRequestBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Failed to send email')
  })

  it('should handle PDF generation timeout gracefully', async () => {
    // PDF生成タイムアウトのモック
    mockFetch.mockRejectedValueOnce(new Error('Timeout'))

    // メール送信のモック
    mockSendMail.mockResolvedValueOnce({ messageId: 'msg-123' })

    const { POST } = await import('./route')
    const request = createMockRequest(validRequestBody)
    const response = await POST(request)
    const data = await response.json()

    // PDF生成が失敗してもメールは送信される
    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(mockSendMail).toHaveBeenCalledTimes(1)
  })

  it('should include correct email content', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: () => Promise.resolve(Buffer.from('mock pdf')),
    })
    mockSendMail.mockResolvedValueOnce({ messageId: 'msg-123' })

    const { POST } = await import('./route')
    const request = createMockRequest(validRequestBody)
    await POST(request)

    const mailOptions = mockSendMail.mock.calls[0][0]

    // HTML内容の検証
    expect(mailOptions.html).toContain('Test User')
    expect(mailOptions.html).toContain('10001') // applicationNumber
    expect(mailOptions.html).toContain('Test Product')
    expect(mailOptions.html).toContain('3点') // partsCount
  })
})
