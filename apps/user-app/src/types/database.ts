export interface Database {
  public: {
    Tables: {
      products: {
        Row: {
          id: string
          name: string
          series_name: string
          country: string
          release_date: string | null
          status: string
          image_url: string | null
          created_at: string
        }
        Insert: Omit<Database['public']['Tables']['products']['Row'], 'created_at'>
        Update: Partial<Database['public']['Tables']['products']['Insert']>
      }
      assembly_pages: {
        Row: {
          id: string
          product_id: string
          page_number: number
          image_url: string | null
          created_at: string
        }
        Insert: Omit<Database['public']['Tables']['assembly_pages']['Row'], 'created_at'>
        Update: Partial<Database['public']['Tables']['assembly_pages']['Insert']>
      }
      assembly_images: {
        Row: {
          id: string
          page_id: string
          assembly_number: string
          display_order: number
          image_url: string | null
          region_x: number | null
          region_y: number | null
          region_width: number | null
          region_height: number | null
          created_at: string
        }
        Insert: Omit<Database['public']['Tables']['assembly_images']['Row'], 'created_at'>
        Update: Partial<Database['public']['Tables']['assembly_images']['Insert']>
      }
      parts: {
        Row: {
          id: string
          name: string | null
          parts_url: string | null
          color: string | null
          parts_code: string | null
          created_at: string
        }
        Insert: Omit<Database['public']['Tables']['parts']['Row'], 'created_at'>
        Update: Partial<Database['public']['Tables']['parts']['Insert']>
      }
      assembly_image_parts: {
        Row: {
          id: string
          assembly_image_id: string
          part_id: string | null
          quantity: number
          display_order: number
          created_at: string
        }
        Insert: Omit<Database['public']['Tables']['assembly_image_parts']['Row'], 'created_at'>
        Update: Partial<Database['public']['Tables']['assembly_image_parts']['Insert']>
      }
      tasks: {
        Row: {
          id: string
          application_number: number  // 申請番号（10000から始まる連番）
          status: string
          flow_type: 'normal' | 'other'  // 'normal'（パーツ選択）or 'other'（パーツ写真）
          zip_code: string
          prefecture: string           // 都道府県（自動入力）
          city: string                 // 市区町村（自動入力）
          town: string | null          // 町域（自動入力）
          address_detail: string       // 番地（手動入力・必須）
          building_name: string | null // 建物名（手動入力・任意）
          email: string
          phone_number: string
          recipient_name: string
          product_name: string
          other_product_name: string | null  // その他フローでユーザーが入力した商品名
          purchase_store: string
          purchase_date: string
          warranty_code: string
          user_memo: string | null
          admin_memo: string | null
          shipment_image_url: string | null
          created_at: string
          updated_at: string
        }
        Insert: Omit<Database['public']['Tables']['tasks']['Row'], 'created_at' | 'updated_at' | 'id' | 'application_number'> & { id?: string }
        Update: Partial<Database['public']['Tables']['tasks']['Insert']>
      }
      task_part_requests: {
        Row: {
          id: string
          task_id: string
          part_id: string
          assembly_image_id: string | null
          quantity: number
          created_at: string
        }
        Insert: Omit<Database['public']['Tables']['task_part_requests']['Row'], 'created_at' | 'id'> & { id?: string }
        Update: Partial<Database['public']['Tables']['task_part_requests']['Insert']>
      }
      task_photo_requests: {
        Row: {
          id: string
          task_id: string
          image_url: string
          display_order: number
          created_at: string
        }
        Insert: Omit<Database['public']['Tables']['task_photo_requests']['Row'], 'created_at' | 'id'> & { id?: string }
        Update: Partial<Database['public']['Tables']['task_photo_requests']['Insert']>
      }
    }
  }
}

// 便利な型エイリアス
export type Product = Database['public']['Tables']['products']['Row']
export type AssemblyPage = Database['public']['Tables']['assembly_pages']['Row']
export type AssemblyImage = Database['public']['Tables']['assembly_images']['Row']
export type Part = Database['public']['Tables']['parts']['Row']
export type AssemblyImagePart = Database['public']['Tables']['assembly_image_parts']['Row']
export type Task = Database['public']['Tables']['tasks']['Row']
export type TaskPartRequest = Database['public']['Tables']['task_part_requests']['Row']
export type TaskPhotoRequest = Database['public']['Tables']['task_photo_requests']['Row']

// 部品と結合したAssemblyImagePart
export interface AssemblyImagePartWithPart extends AssemblyImagePart {
  part: Part | null
}

// 写真パーツデータ（その他フロー用）
export interface PhotoPartData {
  id: string              // クライアント側で生成するユニークID
  originalBlob: Blob      // リサイズ済みのオリジナル画像（WEBP）
  markedBlob: Blob | null // マーキング済み画像（WEBP）、未マーキング時はnull
  previewUrl: string      // プレビュー用のURL（URL.createObjectURL）
}

// 申請フォームのデータ型
export interface ApplicationFormData {
  // Step 1: 送付先情報
  shippingInfo: {
    zipCode: string
    prefecture: string      // 都道府県（自動入力）
    city: string            // 市区町村（自動入力）
    town: string            // 町域（自動入力）
    addressDetail: string   // 番地（手動入力・必須）
    buildingName: string    // 建物名（手動入力・任意）
    email: string
    phoneNumber: string
    recipientName: string
  }
  // Step 2: 購入情報
  purchaseInfo: {
    seriesName: string
    country: string
    productId: string
    productName: string
    otherProductName?: string  // その他フロー時のユーザー入力製品名
    purchaseStore: string
    purchaseDate: string
    warrantyCode: string
  }
  // Step 3: 選択した部品（通常フロー）
  selectedParts: SelectedPart[]
  // Step 3: 写真パーツ（その他フロー）
  photoParts: PhotoPartData[]
  // ユーザー連絡事項
  userMemo: string
}

export interface SelectedPart {
  partId: string
  partName: string | null
  partImageUrl: string | null
  assemblyImageId: string
  assemblyNumber: string
  quantity: number
}
