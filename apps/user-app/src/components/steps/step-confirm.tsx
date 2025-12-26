"use client";

import { useState } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useApplication } from "@/lib/application-context";
import { createTask, createTaskPartRequests, createTaskPhotoRequests, uploadTaskPhoto } from "@/lib/supabase";
import { OTHER_PRODUCT_ID } from "@/components/steps/step-purchase";
import { toast } from "sonner";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Loader2,
  Package,
  MapPin,
  ShoppingBag,
  CheckCircle,
  ImageIcon,
  MessageSquare,
} from "lucide-react";
import { createChildLogger, generateRequestId } from "@/lib/logger";

// Blobをbase64に変換するヘルパー関数（リサイズ付き）
async function blobToBase64(blob: Blob, maxWidth = 600): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = document.createElement('img');
    const url = URL.createObjectURL(blob);

    img.onload = () => {
      URL.revokeObjectURL(url);

      // リサイズが必要か判定
      let width = img.width;
      let height = img.height;
      if (width <= maxWidth) {
        // リサイズ不要: 直接base64化
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
        return;
      }

      // アスペクト比を維持してリサイズ
      const scale = maxWidth / width;
      width = maxWidth;
      height = Math.round(height * scale);

      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Canvas context not available'));
        return;
      }

      ctx.drawImage(img, 0, 0, width, height);

      // JPEG品質80%でbase64化
      const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
      resolve(dataUrl);
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load image'));
    };

    img.src = url;
  });
}

interface StepConfirmProps {
  onComplete: () => void;
  onBack: () => void;
}

export function StepConfirm({ onComplete, onBack }: StepConfirmProps) {
  const { formData, setApplicationNumber, updateUserMemo } = useApplication();

  // 製品名の表示用フォーマット
  const getDisplayProductName = () => {
    if (formData.purchaseInfo.productId === OTHER_PRODUCT_ID) {
      return `その他（上記以外の製品）：${formData.purchaseInfo.otherProductName}`;
    }
    return formData.purchaseInfo.productName;
  };
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 「その他」フローかどうかを判定
  const isOtherFlow = formData.purchaseInfo.productId === OTHER_PRODUCT_ID;

  const handleSubmit = async () => {
    const requestId = generateRequestId();
    const logger = createChildLogger("application-submission", { requestId });
    setError(null);

    // バリデーション
    if (isOtherFlow) {
      if (formData.photoParts.length === 0) {
        logger.warn({ photosCount: 0 }, "No photos uploaded");
        toast.error("不足パーツの写真をアップロードしてください");
        return;
      }
    } else {
      if (formData.selectedParts.length === 0) {
        logger.warn({ partsCount: 0 }, "No parts selected");
        toast.error("申請するパーツを選択してください");
        return;
      }
    }

    logger.info(
      {
        email: formData.shippingInfo.email,
        recipientName: formData.shippingInfo.recipientName,
        flowType: isOtherFlow ? "other" : "normal",
        partsCount: isOtherFlow ? formData.photoParts.length : formData.selectedParts.length,
      },
      "Starting application submission",
    );

    setSubmitting(true);
    try {
      // タスク（申請）を作成
      const task = await createTask({
        zip_code: formData.shippingInfo.zipCode,
        prefecture: formData.shippingInfo.prefecture,
        city: formData.shippingInfo.city,
        town: formData.shippingInfo.town,
        address_detail: formData.shippingInfo.addressDetail,
        building_name: formData.shippingInfo.buildingName,
        email: formData.shippingInfo.email,
        phone_number: formData.shippingInfo.phoneNumber,
        recipient_name: formData.shippingInfo.recipientName,
        product_name: formData.purchaseInfo.productName,
        purchase_store: formData.purchaseInfo.purchaseStore,
        purchase_date: formData.purchaseInfo.purchaseDate,
        warranty_code: formData.purchaseInfo.warrantyCode,
        user_memo: formData.userMemo || undefined,
        flow_type: isOtherFlow ? "other" : "normal",
      });

      if (isOtherFlow) {
        // その他フロー：写真をアップロードしてtask_photo_requestsに保存
        const photoRequests = [];
        for (let i = 0; i < formData.photoParts.length; i++) {
          const photo = formData.photoParts[i];
          // マーキング済み画像があればそれを使用、なければオリジナル
          const blobToUpload = photo.markedBlob || photo.originalBlob;
          const imageUrl = await uploadTaskPhoto(task.id, blobToUpload, i + 1);
          photoRequests.push({
            task_id: task.id,
            image_url: imageUrl,
            display_order: i + 1,
          });
        }

        if (photoRequests.length > 0) {
          await createTaskPhotoRequests(photoRequests);
        }
      } else {
        // 通常フロー：task_part_requestsに保存
        const details = formData.selectedParts.map((part) => ({
          task_id: task.id,
          part_id: part.partId,
          assembly_image_id: part.assemblyImageId,
          quantity: part.quantity,
        }));

        if (details.length > 0) {
          await createTaskPartRequests(details);
        }
      }

      // メール送信API呼び出し
      try {
        // その他フローの場合、写真をbase64に変換
        const partsForPdf = isOtherFlow
          ? await Promise.all(
              formData.photoParts.map(async (photo, index) => {
                const blobToUse = photo.markedBlob || photo.originalBlob;
                const photoBase64 = await blobToBase64(blobToUse);
                return {
                  assemblyNumber: `写真 ${index + 1}`,
                  partName: "写真アップロード",
                  quantity: 1,
                  partImageUrl: null,
                  photoBase64, // PDF埋め込み用のbase64画像
                };
              })
            )
          : formData.selectedParts.map((part) => ({
              assemblyNumber: part.assemblyNumber,
              partName: part.partName || "パーツ",
              quantity: part.quantity,
              partImageUrl: part.partImageUrl,
            }));

        await fetch("/api/send-confirmation", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: formData.shippingInfo.email,
            recipientName: formData.shippingInfo.recipientName,
            taskId: task.id,
            applicationNumber: task.application_number,
            productName: getDisplayProductName(),
            purchaseDate: formData.purchaseInfo.purchaseDate,
            userMemo: formData.userMemo,
            purchaseStore: formData.purchaseInfo.purchaseStore,
            flowType: isOtherFlow ? "other" : "normal",
            partsCount: isOtherFlow ? formData.photoParts.length : formData.selectedParts.length,
            parts: partsForPdf,
          }),
        });
      } catch (emailError) {
        // メール送信失敗はユーザーには通知しない（申請自体は成功）
        logger.warn(
          {
            error:
              emailError instanceof Error
                ? emailError.message
                : "Unknown error",
          },
          "Email sending failed",
        );
      }

      // 申請番号をコンテキストに保存
      if (task.application_number) {
        setApplicationNumber(task.application_number);
      }

      logger.info(
        {
          taskId: task.id,
          applicationNumber: task.application_number,
        },
        "Application completed successfully",
      );
      toast.success("申請が完了しました");
      onComplete();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "不明なエラーが発生しました";
      logger.error(
        {
          error: errorMessage,
          stack: error instanceof Error ? error.stack : undefined,
          email: formData.shippingInfo.email,
        },
        "Application submission failed",
      );
      setError(errorMessage);
      toast.error(`申請に失敗しました: ${errorMessage}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-500" />
          申請内容の確認
        </CardTitle>
        <CardDescription>
          以下の内容で申請します。内容をご確認ください。
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 送付先情報 */}
        <div>
          <h3 className="flex items-center gap-2 font-medium text-slate-700 mb-3">
            <MapPin className="w-4 h-4" />
            送付先情報
          </h3>
          <div className="bg-slate-50 rounded-lg p-4 space-y-2 text-sm">
            <div className="grid grid-cols-3 gap-2">
              <span className="text-slate-500">氏名</span>
              <span className="col-span-2">
                {formData.shippingInfo.recipientName}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <span className="text-slate-500">郵便番号</span>
              <span className="col-span-2">
                {formData.shippingInfo.zipCode}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <span className="text-slate-500">住所</span>
              <span className="col-span-2">
                {formData.shippingInfo.prefecture}
                {formData.shippingInfo.city}
                {formData.shippingInfo.town}
                {formData.shippingInfo.addressDetail}
                {formData.shippingInfo.buildingName && ` ${formData.shippingInfo.buildingName}`}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <span className="text-slate-500">電話番号</span>
              <span className="col-span-2">
                {formData.shippingInfo.phoneNumber}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <span className="text-slate-500">メール</span>
              <span className="col-span-2">{formData.shippingInfo.email}</span>
            </div>
          </div>
        </div>

        <Separator />

        {/* 購入情報 */}
        <div>
          <h3 className="flex items-center gap-2 font-medium text-slate-700 mb-3">
            <ShoppingBag className="w-4 h-4" />
            購入情報
          </h3>
          <div className="bg-slate-50 rounded-lg p-4 space-y-2 text-sm">
            <div className="grid grid-cols-3 gap-2">
              <span className="text-slate-500">製品名</span>
              <span className="col-span-2">
                {getDisplayProductName()}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <span className="text-slate-500">シリーズ</span>
              <span className="col-span-2">
                {formData.purchaseInfo.seriesName}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <span className="text-slate-500">購入店舗</span>
              <span className="col-span-2">
                {formData.purchaseInfo.purchaseStore}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <span className="text-slate-500">購入日</span>
              <span className="col-span-2">
                {formData.purchaseInfo.purchaseDate}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <span className="text-slate-500">部品保証コード</span>
              <span className="col-span-2">
                {formData.purchaseInfo.warrantyCode}
              </span>
            </div>
          </div>
        </div>

        <Separator />

        {/* 選択パーツ または 写真 */}
        <div>
          {isOtherFlow ? (
            <>
              <h3 className="flex items-center gap-2 font-medium text-slate-700 mb-3">
                <ImageIcon className="w-4 h-4" />
                アップロード写真 ({formData.photoParts.length}枚)
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {formData.photoParts.map((photo, index) => (
                  <div
                    key={photo.id}
                    className="border rounded-lg p-2 bg-white"
                  >
                    <div className="relative aspect-square mb-2 bg-slate-50 rounded overflow-hidden">
                      <Image
                        src={photo.previewUrl}
                        alt={`写真 ${index + 1}`}
                        fill
                        className="object-contain p-1"
                      />
                    </div>
                    <p className="text-xs text-slate-600 truncate">
                      写真 {index + 1}
                    </p>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <>
              <h3 className="flex items-center gap-2 font-medium text-slate-700 mb-3">
                <Package className="w-4 h-4" />
                申請パーツ ({formData.selectedParts.length}点)
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {formData.selectedParts.map((part) => (
                  <div
                    key={`${part.partId}-${part.assemblyImageId}`}
                    className="border rounded-lg p-2 bg-white"
                  >
                    <div className="relative aspect-square mb-2 bg-slate-50 rounded overflow-hidden">
                      {part.partImageUrl ? (
                        <Image
                          src={part.partImageUrl}
                          alt={part.partName || "パーツ"}
                          fill
                          className="object-contain p-1"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Package className="w-8 h-8 text-slate-300" />
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-slate-400">
                      組立番号 {part.assemblyNumber}
                    </p>
                    <p className="text-xs text-slate-600 truncate">
                      {part.partName || "パーツ"} x {part.quantity}
                    </p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        <Separator />

        {/* ユーザー連絡事項 */}
        <div>
          <h3 className="flex items-center gap-2 font-medium text-slate-700 mb-3">
            <MessageSquare className="w-4 h-4" />
            申請に関する補足事項（任意）
          </h3>
          <div className="space-y-2">
            <Label htmlFor="userMemo" className="text-sm text-slate-500">
              部品の申請に関して弊社への連絡事項があればご記入ください
            </Label>
            <Textarea
              id="userMemo"
              placeholder="例：申請した部品に関する補足事項など"
              value={formData.userMemo}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => updateUserMemo(e.target.value)}
              rows={3}
              className="resize-none"
              maxLength={500}
            />
            <p className="text-xs text-slate-400 text-right">
              {formData.userMemo.length} / 500文字
            </p>
          </div>
        </div>

        {/* 注意事項 */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
          <p className="font-medium mb-1">ご確認ください</p>
          <ul className="list-disc list-inside space-y-1 text-amber-700">
            <li>申請後の内容変更はできません</li>
            <li>内容を確認し、パーツの準備ができたら、再度ご連絡致します</li>
            <li>確認メールを{formData.shippingInfo.email}にお送りします</li>
          </ul>
        </div>

        {/* エラー表示 */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">
            <p className="font-medium mb-1">エラーが発生しました</p>
            <p className="text-red-700">{error}</p>
            <p className="text-xs text-red-600 mt-2">
              エラーが解決しない場合は、お問い合わせください。
            </p>
          </div>
        )}

        {/* ナビゲーションボタン */}
        <div className="pt-4 flex gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={onBack}
            disabled={submitting}
            className="flex-1"
          >
            戻る
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={
              submitting ||
              (isOtherFlow
                ? formData.photoParts.length === 0
                : formData.selectedParts.length === 0)
            }
            className="flex-1"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                送信中...
              </>
            ) : isOtherFlow ? (
              formData.photoParts.length === 0 ? (
                "写真をアップロードしてください"
              ) : (
                "申請する"
              )
            ) : formData.selectedParts.length === 0 ? (
              "パーツを選択してください"
            ) : (
              "申請する"
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
