'use client'

import { createContext, useContext, useState, ReactNode } from 'react'
import type { ApplicationFormData, SelectedPart, PhotoPartData } from '@/types/database'

interface ApplicationContextType {
  formData: ApplicationFormData
  currentStep: number
  applicationNumber: number | null  // 申請番号
  setCurrentStep: (step: number) => void
  updateShippingInfo: (data: ApplicationFormData['shippingInfo']) => void
  updatePurchaseInfo: (data: ApplicationFormData['purchaseInfo']) => void
  addSelectedPart: (part: SelectedPart) => void
  removeSelectedPart: (partId: string, assemblyImageId: string) => void
  updatePartQuantity: (partId: string, assemblyImageId: string, quantity: number) => void
  clearSelectedParts: () => void
  // 写真パーツ用（その他フロー）
  addPhotoPart: (photo: PhotoPartData) => void
  removePhotoPart: (id: string) => void
  updatePhotoPart: (id: string, markedBlob: Blob, previewUrl: string) => void
  clearPhotoParts: () => void
  // ユーザー連絡事項
  updateUserMemo: (memo: string) => void
  setApplicationNumber: (num: number) => void  // 申請番号を設定
  resetForm: () => void
}

const initialFormData: ApplicationFormData = {
  shippingInfo: {
    zipCode: '',
    prefecture: '',
    city: '',
    town: '',
    addressDetail: '',
    buildingName: '',
    email: '',
    phoneNumber: '',
    recipientName: '',
  },
  purchaseInfo: {
    seriesName: '',
    country: '',
    productId: '',
    productName: '',
    // otherProductName: '',  // オプションなので初期値不要
    purchaseStore: '',
    purchaseDate: '',
    warrantyCode: '',
  },
  selectedParts: [],
  photoParts: [],
  userMemo: '',
}

const ApplicationContext = createContext<ApplicationContextType | undefined>(undefined)

export function ApplicationProvider({ children }: { children: ReactNode }) {
  const [formData, setFormData] = useState<ApplicationFormData>(initialFormData)
  const [currentStep, setCurrentStep] = useState(1)
  const [applicationNumber, setApplicationNumber] = useState<number | null>(null)

  const updateShippingInfo = (data: ApplicationFormData['shippingInfo']) => {
    setFormData(prev => ({ ...prev, shippingInfo: data }))
  }

  const updatePurchaseInfo = (data: ApplicationFormData['purchaseInfo']) => {
    setFormData(prev => ({ ...prev, purchaseInfo: data }))
  }

  const addSelectedPart = (part: SelectedPart) => {
    setFormData(prev => {
      // 同じ部品が既に選択されていないかチェック
      const existing = prev.selectedParts.find(
        p => p.partId === part.partId && p.assemblyImageId === part.assemblyImageId
      )
      if (existing) {
        // 既存の場合は数量を更新
        return {
          ...prev,
          selectedParts: prev.selectedParts.map(p =>
            p.partId === part.partId && p.assemblyImageId === part.assemblyImageId
              ? { ...p, quantity: p.quantity + part.quantity }
              : p
          ),
        }
      }
      // 新規追加
      return { ...prev, selectedParts: [...prev.selectedParts, part] }
    })
  }

  const removeSelectedPart = (partId: string, assemblyImageId: string) => {
    setFormData(prev => ({
      ...prev,
      selectedParts: prev.selectedParts.filter(
        p => !(p.partId === partId && p.assemblyImageId === assemblyImageId)
      ),
    }))
  }

  const updatePartQuantity = (partId: string, assemblyImageId: string, quantity: number) => {
    if (quantity <= 0) {
      removeSelectedPart(partId, assemblyImageId)
      return
    }
    setFormData(prev => ({
      ...prev,
      selectedParts: prev.selectedParts.map(p =>
        p.partId === partId && p.assemblyImageId === assemblyImageId
          ? { ...p, quantity }
          : p
      ),
    }))
  }

  const clearSelectedParts = () => {
    setFormData(prev => ({ ...prev, selectedParts: [] }))
  }

  // 写真パーツ関連の関数（その他フロー用）
  const addPhotoPart = (photo: PhotoPartData) => {
    setFormData(prev => {
      if (prev.photoParts.length >= 10) {
        // 最大10枚まで
        return prev
      }
      return { ...prev, photoParts: [...prev.photoParts, photo] }
    })
  }

  const removePhotoPart = (id: string) => {
    setFormData(prev => ({
      ...prev,
      photoParts: prev.photoParts.filter(p => p.id !== id),
    }))
  }

  const updatePhotoPart = (id: string, markedBlob: Blob, previewUrl: string) => {
    setFormData(prev => ({
      ...prev,
      photoParts: prev.photoParts.map(p =>
        p.id === id ? { ...p, markedBlob, previewUrl } : p
      ),
    }))
  }

  const clearPhotoParts = () => {
    // プレビューURLをrevokeしてメモリを解放
    formData.photoParts.forEach(p => {
      URL.revokeObjectURL(p.previewUrl)
    })
    setFormData(prev => ({ ...prev, photoParts: [] }))
  }

  const updateUserMemo = (memo: string) => {
    setFormData(prev => ({ ...prev, userMemo: memo }))
  }

  const resetForm = () => {
    setFormData(initialFormData)
    setCurrentStep(1)
    setApplicationNumber(null)
  }

  return (
    <ApplicationContext.Provider
      value={{
        formData,
        currentStep,
        applicationNumber,
        setCurrentStep,
        updateShippingInfo,
        updatePurchaseInfo,
        addSelectedPart,
        removeSelectedPart,
        updatePartQuantity,
        clearSelectedParts,
        addPhotoPart,
        removePhotoPart,
        updatePhotoPart,
        clearPhotoParts,
        updateUserMemo,
        setApplicationNumber,
        resetForm,
      }}
    >
      {children}
    </ApplicationContext.Provider>
  )
}

export function useApplication() {
  const context = useContext(ApplicationContext)
  if (!context) {
    throw new Error('useApplication must be used within an ApplicationProvider')
  }
  return context
}
