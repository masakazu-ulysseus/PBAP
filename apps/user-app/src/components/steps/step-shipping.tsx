"use client";

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
import { useApplication } from "@/lib/application-context";

const shippingSchema = z.object({
  zipCode: z
    .string()
    .regex(
      /^\d{3}-?\d{4}$/,
      "郵便番号は「123-4567」または「1234567」の形式で入力してください",
    ),
  address: z.string().min(1, "住所を入力してください"),
  recipientName: z.string().min(1, "氏名を入力してください"),
  phoneNumber: z
    .string()
    .regex(/^[\d-]+$/, "電話番号は数字とハイフンのみ使用できます")
    .min(10, "電話番号を正しく入力してください"),
  email: z.string().email("正しいメールアドレスを入力してください"),
});

type ShippingFormData = z.infer<typeof shippingSchema>;

interface StepShippingProps {
  onNext: () => void;
}

export function StepShipping({ onNext }: StepShippingProps) {
  const { formData, updateShippingInfo } = useApplication();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ShippingFormData>({
    resolver: zodResolver(shippingSchema),
    defaultValues: formData.shippingInfo,
  });

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

          <div className="space-y-2">
            <Label htmlFor="zipCode">
              郵便番号 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="zipCode"
              placeholder="123-4567"
              {...register("zipCode")}
            />
            {errors.zipCode && (
              <p className="text-sm text-red-500">{errors.zipCode.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="address">
              住所 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="address"
              placeholder="東京都渋谷区○○1-2-3 △△マンション101"
              {...register("address")}
            />
            {errors.address && (
              <p className="text-sm text-red-500">{errors.address.message}</p>
            )}
          </div>

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

          <div className="pt-4">
            <Button type="submit" className="w-full">
              次へ進む
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
