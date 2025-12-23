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
import { createTask, createTaskDetails } from "@/lib/supabase";
import { toast } from "sonner";
import {
  Loader2,
  Package,
  MapPin,
  ShoppingBag,
  CheckCircle,
} from "lucide-react";
import { createChildLogger, generateRequestId } from "@/lib/logger";

interface StepConfirmProps {
  onComplete: () => void;
  onBack: () => void;
}

export function StepConfirm({ onComplete, onBack }: StepConfirmProps) {
  const { formData, setApplicationNumber } = useApplication();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    const requestId = generateRequestId();
    const logger = createChildLogger("application-submission", { requestId });
    setError(null);

    // 部品が選択されていない場合はエラー
    if (formData.selectedParts.length === 0) {
      logger.warn({ partsCount: 0 }, "No parts selected");
      toast.error("申請するパーツを選択してください");
      return;
    }

    logger.info(
      {
        email: formData.shippingInfo.email,
        recipientName: formData.shippingInfo.recipientName,
        partsCount: formData.selectedParts.length,
      },
      "Starting application submission",
    );

    setSubmitting(true);
    try {
      // タスク（申請）を作成
      const task = await createTask({
        zip_code: formData.shippingInfo.zipCode,
        address: formData.shippingInfo.address,
        email: formData.shippingInfo.email,
        phone_number: formData.shippingInfo.phoneNumber,
        recipient_name: formData.shippingInfo.recipientName,
        product_name: formData.purchaseInfo.productName,
        purchase_store: formData.purchaseInfo.purchaseStore,
        purchase_date: formData.purchaseInfo.purchaseDate,
        warranty_code: formData.purchaseInfo.warrantyCode,
      });

      // タスク詳細（申請部品）を作成
      const details = formData.selectedParts.map((part) => ({
        task_id: task.id,
        part_id: part.partId,
        assembly_image_id: part.assemblyImageId,
        quantity: part.quantity,
      }));

      if (details.length > 0) {
        await createTaskDetails(details);
      }

      // メール送信API呼び出し
      try {
        await fetch("/api/send-confirmation", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: formData.shippingInfo.email,
            recipientName: formData.shippingInfo.recipientName,
            taskId: task.id,
            applicationNumber: task.application_number, // 申請番号を追加
            productName: formData.purchaseInfo.productName,
            purchaseDate: formData.purchaseInfo.purchaseDate,
            purchaseStore: formData.purchaseInfo.purchaseStore,
            partsCount: formData.selectedParts.length,
            parts: formData.selectedParts.map((part) => ({
              assemblyNumber: part.assemblyNumber,
              partName: part.partName || "パーツ",
              quantity: part.quantity,
              partImageUrl: part.partImageUrl,
            })),
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
                {formData.shippingInfo.address}
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
                {formData.purchaseInfo.productName}
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

        {/* 選択パーツ */}
        <div>
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
            disabled={submitting || formData.selectedParts.length === 0}
            className="flex-1"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                送信中...
              </>
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
