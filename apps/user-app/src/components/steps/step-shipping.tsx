"use client";

import { useState, useEffect, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useApplication } from "@/lib/application-context";
import {
  searchAddressByZipCode,
  normalizeZipCode,
  type ZipCloudAddress,
} from "@/lib/zipcloud";
import { Loader2 } from "lucide-react";

const shippingSchema = z.object({
  zipCode: z
    .string()
    .min(1, "郵便番号を入力してください")
    .regex(
      /^\d{3}-?\d{4}$/,
      "郵便番号は「123-4567」または「1234567」の形式で入力してください"
    ),
  prefecture: z.string().min(1, "都道府県を入力してください"),
  city: z.string().min(1, "市区町村を入力してください"),
  town: z.string(),
  addressDetail: z.string().min(1, "番地を入力してください"),
  buildingName: z.string(),
  recipientName: z.string().min(1, "氏名を入力してください"),
  phoneNumber: z
    .string()
    .regex(/^[\d-]+$/, "電話番号は数字とハイフンのみ使用できます")
    .min(10, "電話番号を正しく入力してください"),
  email: z
    .string()
    .min(1, "メールアドレスを入力してください")
    .email("正しいメールアドレスの形式で入力してください")
    .regex(
      /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/,
      "有効なメールアドレスを入力してください（例: example@email.com）"
    ),
});

type ShippingFormData = z.infer<typeof shippingSchema>;

interface StepShippingProps {
  onNext: () => void;
  onBack: () => void;
}

export function StepShipping({ onNext, onBack }: StepShippingProps) {
  const { formData, updateShippingInfo } = useApplication();

  // 住所検索の状態
  const [isSearching, setIsSearching] = useState(false);
  const [addressResults, setAddressResults] = useState<ZipCloudAddress[]>([]);
  const [showAddressSelect, setShowAddressSelect] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ShippingFormData>({
    resolver: zodResolver(shippingSchema),
    defaultValues: formData.shippingInfo,
  });

  const zipCodeValue = watch("zipCode");
  const prefectureValue = watch("prefecture");
  const cityValue = watch("city");
  const townValue = watch("town");

  // 住所を自動入力する関数
  const applyAddress = useCallback(
    (address: ZipCloudAddress) => {
      setValue("prefecture", address.address1, { shouldValidate: true });
      setValue("city", address.address2, { shouldValidate: true });
      setValue("town", address.address3, { shouldValidate: true });
      setShowAddressSelect(false);
      setSearchError(null);
    },
    [setValue]
  );

  // 郵便番号から住所を検索
  const searchAddress = useCallback(async (zipCode: string) => {
    const normalized = normalizeZipCode(zipCode);

    // 7桁でない場合は検索しない
    if (normalized.length !== 7) {
      return;
    }

    setIsSearching(true);
    setSearchError(null);
    setShowAddressSelect(false);

    try {
      const results = await searchAddressByZipCode(normalized);

      if (results.length === 0) {
        setSearchError("該当する住所が見つかりませんでした");
        setAddressResults([]);
      } else if (results.length === 1) {
        // 1件の場合は自動入力
        setAddressResults(results);
        // applyAddressを直接呼び出し
        const address = results[0];
        setValue("prefecture", address.address1, { shouldValidate: true });
        setValue("city", address.address2, { shouldValidate: true });
        setValue("town", address.address3, { shouldValidate: true });
      } else {
        // 複数件の場合は選択させる
        setAddressResults(results);
        setShowAddressSelect(true);
      }
    } catch {
      setSearchError("住所の検索に失敗しました");
    } finally {
      setIsSearching(false);
    }
  }, [setValue]);

  // 郵便番号が7桁になったら自動検索
  useEffect(() => {
    const normalized = normalizeZipCode(zipCodeValue || "");
    if (normalized.length === 7) {
      searchAddress(zipCodeValue);
    }
  }, [zipCodeValue, searchAddress]);

  // 郵便番号入力時のフォーマット
  const handleZipCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    // 数字とハイフンのみ許可
    const cleaned = value.replace(/[^\d-]/g, "");
    setValue("zipCode", cleaned);
  };

  const onSubmit = (data: ShippingFormData) => {
    updateShippingInfo(data);
    onNext();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>送付先情報</CardTitle>
        <CardDescription>
          パーツをお届けする住所を入力してください
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* 氏名 */}
          <div className="space-y-2">
            <Label htmlFor="recipientName">
              氏名 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="recipientName"
              placeholder="山田 太郎"
              {...register("recipientName")}
            />
            {errors.recipientName && (
              <p className="text-sm text-red-500">
                {errors.recipientName.message}
              </p>
            )}
          </div>

          {/* 郵便番号 */}
          <div className="space-y-2">
            <Label htmlFor="zipCode">
              郵便番号 <span className="text-red-500">*</span>
            </Label>
            <div className="relative">
              <Input
                id="zipCode"
                placeholder="1234567"
                maxLength={8}
                {...register("zipCode")}
                onChange={handleZipCodeChange}
              />
              {isSearching && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              )}
            </div>
            {errors.zipCode && (
              <p className="text-sm text-red-500">{errors.zipCode.message}</p>
            )}
            {searchError && (
              <p className="text-sm text-amber-600">{searchError}</p>
            )}
            <p className="text-xs text-muted-foreground">
              7桁入力すると住所を自動入力します
            </p>
          </div>

          {/* 複数住所選択 */}
          {showAddressSelect && addressResults.length > 1 && (
            <div className="space-y-2 p-3 bg-muted rounded-lg">
              <Label>住所を選択してください</Label>
              <Select
                onValueChange={(value) => {
                  const index = parseInt(value, 10);
                  const selected = addressResults[index];
                  if (selected) {
                    applyAddress(selected);
                  }
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="住所を選択..." />
                </SelectTrigger>
                <SelectContent>
                  {addressResults.map((addr, index) => (
                    <SelectItem key={index} value={index.toString()}>
                      {addr.address1}
                      {addr.address2}
                      {addr.address3}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* 都道府県 */}
          <div className="space-y-2">
            <Label htmlFor="prefecture">
              都道府県 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="prefecture"
              placeholder="東京都"
              className={prefectureValue ? "bg-green-50 border-green-200" : ""}
              {...register("prefecture")}
            />
            {errors.prefecture && (
              <p className="text-sm text-red-500">
                {errors.prefecture.message}
              </p>
            )}
          </div>

          {/* 市区町村 */}
          <div className="space-y-2">
            <Label htmlFor="city">
              市区町村 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="city"
              placeholder="渋谷区"
              className={cityValue ? "bg-green-50 border-green-200" : ""}
              {...register("city")}
            />
            {errors.city && (
              <p className="text-sm text-red-500">{errors.city.message}</p>
            )}
          </div>

          {/* 町域 */}
          <div className="space-y-2">
            <Label htmlFor="town">町域</Label>
            <Input
              id="town"
              placeholder="神宮前"
              className={townValue ? "bg-green-50 border-green-200" : ""}
              {...register("town")}
            />
            {errors.town && (
              <p className="text-sm text-red-500">{errors.town.message}</p>
            )}
          </div>

          {/* 番地 */}
          <div className="space-y-2">
            <Label htmlFor="addressDetail">
              番地 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="addressDetail"
              placeholder="1-2-3"
              {...register("addressDetail")}
            />
            {errors.addressDetail && (
              <p className="text-sm text-red-500">
                {errors.addressDetail.message}
              </p>
            )}
          </div>

          {/* 建物名 */}
          <div className="space-y-2">
            <Label htmlFor="buildingName">建物名（任意）</Label>
            <Input
              id="buildingName"
              placeholder="○○マンション101号室"
              {...register("buildingName")}
            />
            {errors.buildingName && (
              <p className="text-sm text-red-500">
                {errors.buildingName.message}
              </p>
            )}
          </div>

          {/* 電話番号 */}
          <div className="space-y-2">
            <Label htmlFor="phoneNumber">
              電話番号 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="phoneNumber"
              placeholder="090-1234-5678"
              {...register("phoneNumber")}
            />
            {errors.phoneNumber && (
              <p className="text-sm text-red-500">
                {errors.phoneNumber.message}
              </p>
            )}
          </div>

          {/* メールアドレス */}
          <div className="space-y-2">
            <Label htmlFor="email">
              メールアドレス <span className="text-red-500">*</span>
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="example@email.com"
              {...register("email")}
            />
            {errors.email && (
              <p className="text-sm text-red-500">{errors.email.message}</p>
            )}
          </div>

          <div className="pt-4 flex gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={onBack}
              className="flex-1"
            >
              戻る
            </Button>
            <Button type="submit" className="flex-1">
              次へ進む
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
