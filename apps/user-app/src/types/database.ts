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
          size: string | null
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
          zip_code: string
          address: string
          email: string
          phone_number: string
          recipient_name: string
          product_name: string
          purchase_store: string
          purchase_date: string
          warranty_code: string
          admin_memo: string | null
          shipment_image_url: string | null
          created_at: string
          updated_at: string
        }
        Insert: Omit<Database['public']['Tables']['tasks']['Row'], 'created_at' | 'updated_at' | 'id' | 'application_number'> & { id?: string }
        Update: Partial<Database['public']['Tables']['tasks']['Insert']>
      }
      task_details: {
        Row: {
          id: string
          task_id: string
          part_id: string
          assembly_image_id: string | null
          quantity: number
          created_at: string
        }
        Insert: Omit<Database['public']['Tables']['task_details']['Row'], 'created_at' | 'id'> & { id?: string }
        Update: Partial<Database['public']['Tables']['task_details']['Insert']>
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
export type TaskDetail = Database['public']['Tables']['task_details']['Row']

// 部品と結合したAssemblyImagePart
export interface AssemblyImagePartWithPart extends AssemblyImagePart {
  part: Part | null
}

// 申請フォームのデータ型
export interface ApplicationFormData {
  // Step 1: 送付先情報
  shippingInfo: {
    zipCode: string
    address: string
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
    purchaseStore: string
    purchaseDate: string
    warrantyCode: string
  }
  // Step 3: 選択した部品
  selectedParts: SelectedPart[]
}

export interface SelectedPart {
  partId: string
  partName: string | null
  partImageUrl: string | null
  assemblyImageId: string
  assemblyNumber: string
  quantity: number
}
