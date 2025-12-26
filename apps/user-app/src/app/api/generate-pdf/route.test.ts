import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest } from 'next/server'
import { Readable } from 'stream'

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

// @react-pdf/rendererをモック
vi.mock('@react-pdf/renderer', () => ({
  Page: vi.fn(({ children }) => children),
  Text: vi.fn(({ children }) => children),
  View: vi.fn(({ children }) => children),
  Document: vi.fn(({ children }) => children),
  StyleSheet: {
    create: vi.fn((styles) => styles),
  },
  Font: {
    register: vi.fn(),
  },
  Image: vi.fn(() => null),
  renderToBuffer: vi.fn(() => Promise.resolve(Buffer.from('mock pdf content'))),
}))

// sharpをモック
vi.mock('sharp', () => ({
  default: vi.fn(() => ({
    png: vi.fn().mockReturnThis(),
    toBuffer: vi.fn(() => Promise.resolve(Buffer.from('mock png content'))),
  })),
}))

// fsをモック
vi.mock('fs', () => ({
  default: {
    writeFileSync: vi.fn(),
    createReadStream: vi.fn(() => {
      const readable = new Readable()
      readable.push('mock pdf content')
      readable.push(null)
      return readable
    }),
  },
}))

// グローバルfetchをモック（画像取得用）
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

describe('generate-pdf API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const createMockRequest = (body: object) => {
    return new NextRequest('http://localhost:3000/api/generate-pdf', {
      method: 'POST',
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    })
  }

  const validRequestBody = {
    taskId: 'task-123',
    applicationNumber: 10001,
    applicantName: 'Test User',
    applicantEmail: 'test@example.com',
    productName: 'Test Product',
    purchaseDate: '2025-01-01',
    purchaseStore: 'Test Store',
    parts: [
      {
        assemblyNumber: '1',
        partName: 'Part 001',
        quantity: 2,
        partImageUrl: 'http://example.com/part1.webp',
      },
      {
        assemblyNumber: '2',
        partName: 'Part 002',
        quantity: 1,
        partImageUrl: null,
      },
    ],
  }

  it('should generate PDF successfully', async () => {
    // 画像取得のモック
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'image/webp' }),
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(100)),
    })

    const { POST } = await import('./route')
    const request = createMockRequest(validRequestBody)
    const response = await POST(request)

    expect(response.status).toBe(200)
    expect(response.headers.get('Content-Type')).toBe('application/pdf')
    expect(response.headers.get('Content-Disposition')).toContain('task-123')
  })

  it('should handle parts without images', async () => {
    const bodyWithoutImages = {
      ...validRequestBody,
      parts: [
        { assemblyNumber: '1', partName: 'Part 001', quantity: 2, partImageUrl: null },
      ],
    }

    const { POST } = await import('./route')
    const request = createMockRequest(bodyWithoutImages)
    const response = await POST(request)

    expect(response.status).toBe(200)
    // 画像取得は呼ばれない
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('should handle image fetch failure gracefully', async () => {
    // 画像取得失敗のモック
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    })

    const { POST } = await import('./route')
    const request = createMockRequest(validRequestBody)
    const response = await POST(request)

    // 画像取得が失敗してもPDF生成は成功する
    expect(response.status).toBe(200)
  })

  it('should handle network error during image fetch', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    const { POST } = await import('./route')
    const request = createMockRequest(validRequestBody)
    const response = await POST(request)

    // ネットワークエラーでもPDF生成は成功する
    expect(response.status).toBe(200)
  })

  it('should convert WebP images to PNG', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'image/webp' }),
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(100)),
    })

    const { POST } = await import('./route')
    const request = createMockRequest(validRequestBody)
    await POST(request)

    // sharpが呼ばれたことを確認
    const sharp = (await import('sharp')).default
    expect(sharp).toHaveBeenCalled()
  })

  it('should return 500 on PDF generation error', async () => {
    // renderToBufferがエラーを投げるようにモック
    const { renderToBuffer } = await import('@react-pdf/renderer')
    vi.mocked(renderToBuffer).mockRejectedValueOnce(new Error('PDF generation failed'))

    const { POST } = await import('./route')
    const request = createMockRequest(validRequestBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Failed to generate PDF')
  })

  it('should set correct filename in Content-Disposition header', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'image/jpeg' }),
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(100)),
    })

    const { POST } = await import('./route')
    const request = createMockRequest(validRequestBody)
    const response = await POST(request)

    const contentDisposition = response.headers.get('Content-Disposition')
    expect(contentDisposition).toBe('attachment; filename="application_task-123.pdf"')
  })
})
