"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useApplication } from "@/lib/application-context";
import { getProducts } from "@/lib/supabase";
import { validateWarrantyCode } from "@/lib/warranty";
import type { Product } from "@/types/database";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertCircle,
  CalendarIcon,
  CheckCircle2,
  Loader2,
  Package,
} from "lucide-react";
import { cn } from "@/lib/utils";

// 「その他」製品用の特別なID
export const OTHER_PRODUCT_ID = "__OTHER__";

const purchaseSchema = z.object({
  seriesName: z.string(),
  country: z.string(),
  productId: z.string().min(1, "製品を選択してください"),
  productName: z.string(),
  otherProductName: z.string().optional(),
  purchaseStore: z.string().min(1, "購入店舗を入力してください"),
  purchaseDate: z.string().min(1, "購入日を入力してください"),
  warrantyCode: z
    .string()
    .length(6, "部品保証コードは6桁です")
    .regex(/^\d{6}$/, "部品保証コードは数字6桁で入力してください")
    .refine(validateWarrantyCode, "部品保証コードが正しくありません"),
}).refine((data) => {
  // その他選択時は otherProductName が必須
  if (data.productId === OTHER_PRODUCT_ID) {
    return data.otherProductName && data.otherProductName.trim().length > 0;
  }
  return true;
}, {
  message: "製品名を入力してください",
  path: ["otherProductName"],
});

type PurchaseFormData = z.infer<typeof purchaseSchema>;

interface StepPurchaseProps {
  onNext: () => void;
  onBack?: () => void;
}

export function StepPurchase({ onNext, onBack }: StepPurchaseProps) {
  const { formData, updatePurchaseInfo } = useApplication();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [showWarrantyCodeImage, setShowWarrantyCodeImage] = useState(false);
  const [storeType, setStoreType] = useState<string>("unselected"); // 購入店舗の種別

  const purchaseStoreOptions = [
    { value: "unselected", label: "選択してください" },
    { value: "official", label: "パンツァーブロックス公式ショップ" },
    { value: "retail", label: "模型店・販売店" },
    { value: "other", label: "その他" },
  ];

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<PurchaseFormData>({
    resolver: zodResolver(purchaseSchema),
    defaultValues: formData.purchaseInfo,
  });

  const warrantyCode = watch("warrantyCode");
  const watchedPurchaseStore = watch("purchaseStore");

  // 既存の購入情報から店舗種別を判定して初期値を設定
  useEffect(() => {
    if (formData.purchaseInfo.purchaseStore) {
      const existingStore = formData.purchaseInfo.purchaseStore;
      if (existingStore === "パンツァーブロックス公式ショップ") {
        setStoreType("official");
      } else if (existingStore === "模型店・販売店") {
        setStoreType("retail");
      } else {
        setStoreType("other");
      }
    }
  }, []);

  // 製品一覧を取得
  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const productsData = await getProducts();
        setProducts(productsData);
      } catch (error) {
        console.error("Error fetching products:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchProducts();
  }, []);

  const onSubmit = (data: PurchaseFormData) => {
    updatePurchaseInfo(data);
    onNext();
  };

  const isWarrantyValid =
    warrantyCode?.length === 6 && validateWarrantyCode(warrantyCode);
  const showWarrantyStatus = warrantyCode?.length === 6;

  if (loading) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-slate-400" />
          <p className="mt-2 text-slate-500">読み込み中...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>購入情報</CardTitle>
        <CardDescription>
          製品の購入情報と部品保証コードを入力してください
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label>
              製品 <span className="text-red-500">*</span>
            </Label>
            <Select
              value={watch("productId")}
              onValueChange={(value) => {
                if (value === OTHER_PRODUCT_ID) {
                  // 「その他」選択時
                  setValue("productId", OTHER_PRODUCT_ID);
                  setValue("productName", "その他");
                  setValue("seriesName", "");
                  setValue("country", "");
                } else {
                  const product = products.find((p) => p.id === value);
                  setValue("productId", value);
                  setValue("productName", product?.name || "");
                  setValue("seriesName", product?.series_name || "");
                  setValue("country", product?.country || "");
                }
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="製品を選択してください" />
              </SelectTrigger>
              <SelectContent>
                {products.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
                <SelectItem value={OTHER_PRODUCT_ID} className="border-t mt-1 pt-1">
                  その他（上記以外の製品）
                </SelectItem>
              </SelectContent>
            </Select>
            {errors.productId && (
              <p className="text-sm text-red-500">{errors.productId.message}</p>
            )}

            {/* 選択された製品の画像を表示 */}
            {watch("productId") &&
              (() => {
                const productId = watch("productId");

                // 「その他」選択時
                if (productId === OTHER_PRODUCT_ID) {
                  return (
                    <div className="mt-3 space-y-3">
                      <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                        <div className="flex items-center gap-2 text-amber-700">
                          <AlertCircle className="w-5 h-5" />
                          <p className="text-sm font-medium">
                            その他の製品を選択しました
                          </p>
                        </div>
                        <p className="text-xs text-amber-600 mt-1">
                          次の画面で不足部品の写真をアップロードしていただきます
                        </p>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="otherProductName">
                          製品名を入力してください <span className="text-red-500">*</span>
                        </Label>
                        <Input
                          id="otherProductName"
                          placeholder="例：超重戦車マウス、Ⅱ号戦車 L型、マルダーⅢ H型"
                          {...register("otherProductName", {
                            required: watch("productId") === OTHER_PRODUCT_ID,
                          })}
                        />
                        {errors.otherProductName && (
                          <p className="text-sm text-red-500">
                            製品名を入力してください
                          </p>
                        )}
                      </div>
                    </div>
                  );
                }

                const selectedProduct = products.find(
                  (p) => p.id === productId,
                );
                if (selectedProduct?.image_url) {
                  return (
                    <div className="mt-3 p-3 bg-slate-50 rounded-lg border">
                      <div className="relative w-full aspect-[4/3] max-w-xs mx-auto">
                        <Image
                          src={selectedProduct.image_url}
                          alt={selectedProduct.name}
                          fill
                          className="object-contain rounded"
                        />
                      </div>
                      <p className="text-center text-sm text-slate-600 mt-2">
                        {selectedProduct.name}
                      </p>
                    </div>
                  );
                } else if (selectedProduct) {
                  return (
                    <div className="mt-3 p-3 bg-slate-50 rounded-lg border">
                      <div className="w-full aspect-[4/3] max-w-xs mx-auto flex items-center justify-center bg-slate-100 rounded">
                        <Package className="w-12 h-12 text-slate-300" />
                      </div>
                      <p className="text-center text-sm text-slate-600 mt-2">
                        {selectedProduct.name}
                      </p>
                    </div>
                  );
                }
                return null;
              })()}
          </div>

          <div className="space-y-2">
            <Label htmlFor="purchaseStoreType">
              購入店舗 <span className="text-red-500">*</span>
            </Label>
            <Select
              value={storeType}
              onValueChange={(value) => {
                setStoreType(value);
                // プリセット選択時は即座にpurchaseStoreを設定
                if (value !== "other") {
                  const selected = purchaseStoreOptions.find((opt) => opt.value === value);
                  setValue("purchaseStore", selected?.label || "");
                } else {
                  setValue("purchaseStore", ""); // その他の場合は一旦クリア
                }
              }}
            >
              <SelectTrigger id="purchaseStoreType">
                <SelectValue placeholder="購入店舗を選択してください" />
              </SelectTrigger>
              <SelectContent>
                {purchaseStoreOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {storeType === "other" && (
              <Input
                placeholder="店舗名を入力してください"
                {...register("purchaseStore", {
                  required: storeType === "other",
                })}
                className="mt-2"
              />
            )}
            {errors.purchaseStore && (
              <p className="text-sm text-red-500">
                {errors.purchaseStore.message}
              </p>
            )}
            {!errors.purchaseStore && storeType === "unselected" && (
              <p className="text-sm text-red-500">
                購入店舗を選択してください
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label>
              購入日 <span className="text-red-500">*</span>
            </Label>
            <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  className={cn(
                    "w-full justify-start text-left font-normal",
                    !watch("purchaseDate") && "text-muted-foreground",
                  )}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {watch("purchaseDate")
                    ? format(new Date(watch("purchaseDate")), "yyyy年M月d日", {
                        locale: ja,
                      })
                    : "日付を選択してください"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={
                    watch("purchaseDate")
                      ? new Date(watch("purchaseDate"))
                      : undefined
                  }
                  onSelect={(date) => {
                    if (date) {
                      setValue("purchaseDate", format(date, "yyyy-MM-dd"), {
                        shouldValidate: true,
                      });
                    }
                    setCalendarOpen(false);
                  }}
                  disabled={(date) => date > new Date()}
                  locale={ja}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
            {errors.purchaseDate && (
              <p className="text-sm text-red-500">
                {errors.purchaseDate.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="warrantyCode">
              部品保証コード <span className="text-red-500">*</span>
            </Label>
            <div className="relative">
              <Input
                id="warrantyCode"
                placeholder="123456"
                maxLength={6}
                {...register("warrantyCode")}
                className={
                  showWarrantyStatus
                    ? isWarrantyValid
                      ? "pr-10 border-green-500"
                      : "pr-10 border-red-500"
                    : ""
                }
              />
              {showWarrantyStatus && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  {isWarrantyValid ? (
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-red-500" />
                  )}
                </div>
              )}
            </div>
            {errors.warrantyCode && (
              <p className="text-sm text-red-500">
                {errors.warrantyCode.message}
              </p>
            )}
            <p className="text-xs text-slate-500">
              製品に付属の
              <button
                type="button"
                onClick={() => setShowWarrantyCodeImage(true)}
                className="text-blue-600 font-medium hover:text-blue-700 underline mx-0.5"
              >
                部品保証コード
              </button>
              （6桁）の数字を入力してください
            </p>
          </div>

          <div className="pt-4 flex gap-3">
            {onBack && (
              <Button
                type="button"
                variant="outline"
                onClick={onBack}
                className="flex-1"
              >
                戻る
              </Button>
            )}
            <Button type="submit" className={onBack ? "flex-1" : "w-full"}>
              次へ進む
            </Button>
          </div>
        </form>
      </CardContent>

      {/* Warranty Code Image Dialog */}
      <Dialog
        open={showWarrantyCodeImage}
        onOpenChange={setShowWarrantyCodeImage}
      >
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>部品保証コードについて</DialogTitle>
          </DialogHeader>
          <div className="relative w-full">
            <Image
              src="/images/Notice_to_purchasers.webp"
              alt="部品保証コードの説明"
              width={800}
              height={600}
              className="w-full h-auto rounded-lg"
            />
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
