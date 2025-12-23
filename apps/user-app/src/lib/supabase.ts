import { createClient } from '@supabase/supabase-js'
import type { Task, TaskDetail, Part, Product, AssemblyPage, AssemblyImage } from '@/types/database'
import { createChildLogger, generateRequestId } from '@/lib/logger'

// 部品付き組立画像パーツの型
interface AssemblyImagePartWithPart {
  id: string
  display_order: number
  quantity: number
  part: Part | null
}

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// 商品一覧を取得
export async function getProducts(): Promise<Product[]> {
  const requestId = generateRequestId()
  const dbLogger = createChildLogger('getProducts', { requestId })

  dbLogger.debug('Fetching products')

  const startTime = Date.now()
  const { data, error } = await supabase
    .from('products')
    .select('*')
    .order('name')
  const duration = Date.now() - startTime

  if (error) {
    dbLogger.error({
      error: error.message,
      code: error.code,
      duration
    }, 'Failed to fetch products')
    throw error
  }

  dbLogger.info({
    count: data?.length || 0,
    duration
  }, 'Products fetched successfully')
  return data as Product[]
}

// シリーズ一覧を取得（重複なし）
export async function getSeries(): Promise<string[]> {
  const { data, error } = await supabase
    .from('products')
    .select('series_name')

  if (error) throw error

  // 重複を除去
  const typedData = data as { series_name: string }[]
  const uniqueSeries = [...new Set(typedData.map(p => p.series_name))]
  return uniqueSeries.filter(Boolean).sort()
}

// 国一覧を取得（重複なし）
export async function getCountries(): Promise<string[]> {
  const { data, error } = await supabase
    .from('products')
    .select('country')

  if (error) throw error

  // 重複を除去
  const typedData = data as { country: string }[]
  const uniqueCountries = [...new Set(typedData.map(p => p.country))]
  return uniqueCountries.filter(Boolean).sort()
}

// シリーズと国で商品をフィルタ
export async function getProductsBySeriesAndCountry(seriesName: string, country: string): Promise<Product[]> {
  const { data, error } = await supabase
    .from('products')
    .select('*')
    .eq('series_name', seriesName)
    .eq('country', country)
    .order('name')

  if (error) throw error
  return data as Product[]
}

// 商品の組立ページ一覧を取得
export async function getAssemblyPages(productId: string): Promise<AssemblyPage[]> {
  const { data, error } = await supabase
    .from('assembly_pages')
    .select('*')
    .eq('product_id', productId)
    .not('image_url', 'is', null)
    .order('page_number')

  if (error) throw error
  return data as AssemblyPage[]
}

// 組立ページの組立番号画像一覧を取得
export async function getAssemblyImages(pageId: string): Promise<AssemblyImage[]> {
  const { data, error } = await supabase
    .from('assembly_images')
    .select('*')
    .eq('page_id', pageId)
    .not('image_url', 'is', null)
    .order('display_order')

  if (error) throw error
  return data as AssemblyImage[]
}

// 組立番号画像の部品一覧を取得
export async function getPartsForAssemblyImage(assemblyImageId: string): Promise<AssemblyImagePartWithPart[]> {
  const { data, error } = await supabase
    .from('assembly_image_parts')
    .select(`
      id,
      display_order,
      quantity,
      part:parts (
        id,
        name,
        parts_url,
        color,
        size
      )
    `)
    .eq('assembly_image_id', assemblyImageId)
    .not('part_id', 'is', null)
    .order('display_order')

  if (error) throw error
  return data as unknown as AssemblyImagePartWithPart[]
}

// タスク（申請）を作成
export async function createTask(taskData: {
  zip_code: string
  address: string
  email: string
  phone_number: string
  recipient_name: string
  product_name: string
  purchase_store: string
  purchase_date: string
  warranty_code: string
}): Promise<Task> {
  // UUIDを生成
  const taskId = crypto.randomUUID()
  const requestId = generateRequestId()
  const dbLogger = createChildLogger('createTask', { requestId })

  dbLogger.info({
    taskId,
    email: taskData.email,
    recipientName: taskData.recipient_name,
    productName: taskData.product_name
  }, 'Creating task')

  const startTime = Date.now()
  const { data, error } = await supabase
    .from('tasks')
    .insert({
      id: taskId,
      ...taskData,
      status: 'pending'
    })
    .select()
    .single()
  const duration = Date.now() - startTime

  if (error) {
    dbLogger.error({
      taskId,
      error: error.message,
      code: error.code,
      duration
    }, 'Failed to create task')
    throw new Error(`タスク作成エラー: ${error.message} (code: ${error.code})`)
  }

  dbLogger.info({
    taskId,
    applicationNumber: (data as Task).application_number,
    duration
  }, 'Task created successfully')
  return data as Task
}

// タスク詳細（申請部品）を作成
export async function createTaskDetails(details: {
  task_id: string
  part_id: string
  assembly_image_id: string
  quantity: number
}[]): Promise<TaskDetail[]> {
  const requestId = generateRequestId()
  const dbLogger = createChildLogger('createTaskDetails', { requestId })

  dbLogger.info({
    taskId: details[0]?.task_id,
    partsCount: details.length
  }, 'Creating task details')

  const startTime = Date.now()
  const { data, error } = await supabase
    .from('task_details')
    .insert(details)
    .select()
  const duration = Date.now() - startTime

  if (error) {
    dbLogger.error({
      taskId: details[0]?.task_id,
      error: error.message,
      code: error.code,
      duration
    }, 'Failed to create task details')
    throw new Error(`タスク詳細作成エラー: ${error.message} (code: ${error.code})`)
  }

  dbLogger.info({
    taskId: details[0]?.task_id,
    partsCount: data?.length || 0,
    duration
  }, 'Task details created successfully')
  return data as TaskDetail[]
}
