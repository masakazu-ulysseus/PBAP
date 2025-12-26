import { createClient } from '@supabase/supabase-js'
import type { Task, TaskPartRequest, TaskPhotoRequest, Part, Product, AssemblyPage, AssemblyImage } from '@/types/database'
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
  prefecture: string
  city: string
  town: string
  address_detail: string
  building_name: string
  email: string
  phone_number: string
  recipient_name: string
  product_name: string
  purchase_store: string
  purchase_date: string
  warranty_code: string
  user_memo?: string
  flow_type: 'normal' | 'other'
}): Promise<Task> {
  // UUIDを生成
  const taskId = crypto.randomUUID()
  const requestId = generateRequestId()
  const dbLogger = createChildLogger('createTask', { requestId })

  dbLogger.info({
    taskId,
    email: taskData.email,
    recipientName: taskData.recipient_name,
    productName: taskData.product_name,
    flowType: taskData.flow_type
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

// タスクパーツリクエスト（申請部品）を作成 - 通常フロー用
export async function createTaskPartRequests(details: {
  task_id: string
  part_id: string
  assembly_image_id: string
  quantity: number
}[]): Promise<TaskPartRequest[]> {
  const requestId = generateRequestId()
  const dbLogger = createChildLogger('createTaskPartRequests', { requestId })

  dbLogger.info({
    taskId: details[0]?.task_id,
    partsCount: details.length
  }, 'Creating task part requests')

  const startTime = Date.now()
  const { data, error } = await supabase
    .from('task_part_requests')
    .insert(details)
    .select()
  const duration = Date.now() - startTime

  if (error) {
    dbLogger.error({
      taskId: details[0]?.task_id,
      error: error.message,
      code: error.code,
      duration
    }, 'Failed to create task part requests')
    throw new Error(`タスクパーツリクエスト作成エラー: ${error.message} (code: ${error.code})`)
  }

  dbLogger.info({
    taskId: details[0]?.task_id,
    partsCount: data?.length || 0,
    duration
  }, 'Task part requests created successfully')
  return data as TaskPartRequest[]
}

// タスク写真リクエスト（アップロード写真）を作成 - その他フロー用
export async function createTaskPhotoRequests(photos: {
  task_id: string
  image_url: string
  display_order: number
}[]): Promise<TaskPhotoRequest[]> {
  const requestId = generateRequestId()
  const dbLogger = createChildLogger('createTaskPhotoRequests', { requestId })

  dbLogger.info({
    taskId: photos[0]?.task_id,
    photosCount: photos.length
  }, 'Creating task photo requests')

  const startTime = Date.now()
  const { data, error } = await supabase
    .from('task_photo_requests')
    .insert(photos)
    .select()
  const duration = Date.now() - startTime

  if (error) {
    dbLogger.error({
      taskId: photos[0]?.task_id,
      error: error.message,
      code: error.code,
      duration
    }, 'Failed to create task photo requests')
    throw new Error(`タスク写真リクエスト作成エラー: ${error.message} (code: ${error.code})`)
  }

  dbLogger.info({
    taskId: photos[0]?.task_id,
    photosCount: data?.length || 0,
    duration
  }, 'Task photo requests created successfully')
  return data as TaskPhotoRequest[]
}

// 画像をSupabase Storageにアップロード
export async function uploadTaskPhoto(taskId: string, photoBlob: Blob, displayOrder: number): Promise<string> {
  const requestId = generateRequestId()
  const dbLogger = createChildLogger('uploadTaskPhoto', { requestId })

  const fileName = `task-photos/${taskId}/${displayOrder}.webp`

  dbLogger.info({
    taskId,
    fileName,
    size: photoBlob.size
  }, 'Uploading task photo')

  const startTime = Date.now()
  const { data, error } = await supabase
    .storage
    .from('product-images')
    .upload(fileName, photoBlob, {
      contentType: 'image/webp',
      upsert: true
    })
  const duration = Date.now() - startTime

  if (error) {
    dbLogger.error({
      taskId,
      fileName,
      error: error.message,
      duration
    }, 'Failed to upload task photo')
    throw new Error(`画像アップロードエラー: ${error.message}`)
  }

  // 公開URLを取得
  const { data: urlData } = supabase
    .storage
    .from('product-images')
    .getPublicUrl(fileName)

  dbLogger.info({
    taskId,
    fileName,
    url: urlData.publicUrl,
    duration
  }, 'Task photo uploaded successfully')

  return urlData.publicUrl
}
