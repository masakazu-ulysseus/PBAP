import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// loggerをモック
vi.mock('@/lib/logger', () => ({
  createChildLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
  }),
  generateRequestId: () => 'test-request-id',
}))

// Supabaseクライアントのモック関数
const mockFrom = vi.fn()
const mockSelect = vi.fn()
const mockInsert = vi.fn()
const mockEq = vi.fn()
const mockNot = vi.fn()
const mockOrder = vi.fn()
const mockSingle = vi.fn()

// Supabaseクライアントをモック
vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn(() => ({
    from: mockFrom,
  })),
}))

describe('supabase', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // チェーン可能なモックを設定
    mockFrom.mockReturnValue({
      select: mockSelect,
      insert: mockInsert,
    })
    mockSelect.mockReturnValue({
      eq: mockEq,
      not: mockNot,
      order: mockOrder,
      single: mockSingle,
    })
    mockInsert.mockReturnValue({
      select: mockSelect,
    })
    mockEq.mockReturnValue({
      eq: mockEq,
      not: mockNot,
      order: mockOrder,
    })
    mockNot.mockReturnValue({
      order: mockOrder,
      eq: mockEq,
      not: mockNot,
    })
    mockOrder.mockReturnValue({
      eq: mockEq,
      not: mockNot,
    })
  })

  afterEach(() => {
    vi.resetModules()
  })

  describe('getProducts', () => {
    it('should fetch products successfully', async () => {
      const mockProducts = [
        { id: '1', name: 'Product A', series_name: 'Series 1', country: 'Germany' },
        { id: '2', name: 'Product B', series_name: 'Series 2', country: 'USA' },
      ]

      mockOrder.mockResolvedValue({ data: mockProducts, error: null })

      const { getProducts } = await import('./supabase')
      const result = await getProducts()

      expect(result).toEqual(mockProducts)
      expect(mockFrom).toHaveBeenCalledWith('products')
    })

    it('should throw error on failure', async () => {
      const mockError = { message: 'Database error', code: 'DB001' }
      mockOrder.mockResolvedValue({ data: null, error: mockError })

      const { getProducts } = await import('./supabase')

      await expect(getProducts()).rejects.toEqual(mockError)
    })
  })

  describe('getSeries', () => {
    it('should return unique series names sorted', async () => {
      const mockData = [
        { series_name: 'Series C' },
        { series_name: 'Series A' },
        { series_name: 'Series A' }, // 重複
        { series_name: 'Series B' },
      ]

      // getSeries は .select().eq() のチェーン
      mockEq.mockResolvedValue({ data: mockData, error: null })

      const { getSeries } = await import('./supabase')
      const result = await getSeries()

      expect(result).toEqual(['Series A', 'Series B', 'Series C'])
    })

    it('should filter out empty series names', async () => {
      const mockData = [
        { series_name: 'Series A' },
        { series_name: '' },
        { series_name: null },
        { series_name: 'Series B' },
      ]

      // getSeries は .select().eq() のチェーン
      mockEq.mockResolvedValue({ data: mockData, error: null })

      const { getSeries } = await import('./supabase')
      const result = await getSeries()

      expect(result).toEqual(['Series A', 'Series B'])
    })
  })

  describe('getCountries', () => {
    it('should return unique country names sorted', async () => {
      const mockData = [
        { country: 'USA' },
        { country: 'Germany' },
        { country: 'Germany' }, // 重複
        { country: 'Japan' },
      ]

      // getCountries は .select().eq() のチェーン
      mockEq.mockResolvedValue({ data: mockData, error: null })

      const { getCountries } = await import('./supabase')
      const result = await getCountries()

      expect(result).toEqual(['Germany', 'Japan', 'USA'])
    })
  })

  describe('createTask', () => {
    it('should create task with correct data', async () => {
      const mockTask = {
        id: 'test-uuid',
        application_number: 10001,
        zip_code: '123-4567',
        address: 'Tokyo',
        email: 'test@example.com',
        phone_number: '090-1234-5678',
        recipient_name: 'Test User',
        product_name: 'Test Product',
        purchase_store: 'Test Store',
        purchase_date: '2025-01-01',
        warranty_code: '100003',
        status: 'pending',
      }

      mockSingle.mockResolvedValue({ data: mockTask, error: null })

      const { createTask } = await import('./supabase')
      const result = await createTask({
        zip_code: '123-4567',
        prefecture: '東京都',
        city: '渋谷区',
        town: '神宮前',
        address_detail: '1-2-3',
        building_name: '',
        email: 'test@example.com',
        phone_number: '090-1234-5678',
        recipient_name: 'Test User',
        product_name: 'Test Product',
        purchase_store: 'Test Store',
        purchase_date: '2025-01-01',
        warranty_code: '100003',
        flow_type: 'normal',
      })

      expect(result).toEqual(mockTask)
      expect(result.application_number).toBe(10001)
      expect(mockFrom).toHaveBeenCalledWith('tasks')
    })

    it('should throw error with formatted message on failure', async () => {
      const mockError = { message: 'Insert failed', code: 'INS001' }
      mockSingle.mockResolvedValue({ data: null, error: mockError })

      const { createTask } = await import('./supabase')

      await expect(createTask({
        zip_code: '123-4567',
        prefecture: '東京都',
        city: '渋谷区',
        town: '神宮前',
        address_detail: '1-2-3',
        building_name: '',
        email: 'test@example.com',
        phone_number: '090-1234-5678',
        recipient_name: 'Test User',
        product_name: 'Test Product',
        purchase_store: 'Test Store',
        purchase_date: '2025-01-01',
        warranty_code: '100003',
        flow_type: 'normal',
      })).rejects.toThrow('タスク作成エラー: Insert failed (code: INS001)')
    })
  })

  describe('createTaskPartRequests', () => {
    it('should create task part requests successfully', async () => {
      const mockDetails = [
        { id: '1', task_id: 'task-1', part_id: 'part-1', assembly_image_id: 'img-1', quantity: 2 },
        { id: '2', task_id: 'task-1', part_id: 'part-2', assembly_image_id: 'img-1', quantity: 1 },
      ]

      mockSelect.mockResolvedValue({ data: mockDetails, error: null })

      const { createTaskPartRequests } = await import('./supabase')
      const result = await createTaskPartRequests([
        { task_id: 'task-1', part_id: 'part-1', assembly_image_id: 'img-1', quantity: 2 },
        { task_id: 'task-1', part_id: 'part-2', assembly_image_id: 'img-1', quantity: 1 },
      ])

      expect(result).toEqual(mockDetails)
      expect(result.length).toBe(2)
      expect(mockFrom).toHaveBeenCalledWith('task_part_requests')
    })

    it('should throw error with formatted message on failure', async () => {
      const mockError = { message: 'Insert failed', code: 'INS002' }
      mockSelect.mockResolvedValue({ data: null, error: mockError })

      const { createTaskPartRequests } = await import('./supabase')

      await expect(createTaskPartRequests([
        { task_id: 'task-1', part_id: 'part-1', assembly_image_id: 'img-1', quantity: 2 },
      ])).rejects.toThrow('タスクパーツリクエスト作成エラー: Insert failed (code: INS002)')
    })
  })

  describe('getAssemblyPages', () => {
    it('should fetch assembly pages for product', async () => {
      const mockPages = [
        { id: '1', product_id: 'prod-1', page_number: 1, image_url: 'http://example.com/1.webp' },
        { id: '2', product_id: 'prod-1', page_number: 2, image_url: 'http://example.com/2.webp' },
      ]

      mockOrder.mockResolvedValue({ data: mockPages, error: null })

      const { getAssemblyPages } = await import('./supabase')
      const result = await getAssemblyPages('prod-1')

      expect(result).toEqual(mockPages)
      expect(mockFrom).toHaveBeenCalledWith('assembly_pages')
      expect(mockEq).toHaveBeenCalledWith('product_id', 'prod-1')
    })
  })

  describe('getAssemblyImages', () => {
    it('should fetch assembly images for page', async () => {
      const mockImages = [
        { id: '1', page_id: 'page-1', assembly_number: '1', image_url: 'http://example.com/a1.webp' },
        { id: '2', page_id: 'page-1', assembly_number: '2', image_url: 'http://example.com/a2.webp' },
      ]

      mockOrder.mockResolvedValue({ data: mockImages, error: null })

      const { getAssemblyImages } = await import('./supabase')
      const result = await getAssemblyImages('page-1')

      expect(result).toEqual(mockImages)
      expect(mockFrom).toHaveBeenCalledWith('assembly_images')
      expect(mockEq).toHaveBeenCalledWith('page_id', 'page-1')
    })
  })
})
