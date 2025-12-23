"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useApplication } from "@/lib/application-context";
import { CheckCircle, Mail, Home } from "lucide-react";

export function StepComplete() {
  const { formData, applicationNumber, resetForm } = useApplication();

  return (
    <Card>
      <CardContent className="py-12 text-center space-y-6">
        <div className="flex justify-center">
          <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center">
            <CheckCircle className="w-10 h-10 text-green-500" />
          </div>
        </div>

        <div>
          <h2 className="text-2xl font-bold text-slate-800 mb-2">
            申請が完了しました
          </h2>
          <p className="text-slate-600">パーツ申請を受け付けました。</p>
          {applicationNumber && (
            <p className="text-lg font-semibold text-green-600 mt-2">
              申請番号: #{applicationNumber}
            </p>
          )}
        </div>

        <div className="bg-slate-50 rounded-lg p-4 max-w-md mx-auto">
          <div className="flex items-center justify-center gap-2 text-slate-600 mb-2">
            <Mail className="w-4 h-4" />
            <span className="text-sm">確認メールを送信しました</span>
          </div>
          <p className="text-sm text-slate-500">
            {formData.shippingInfo.email}
          </p>
          <p className="text-xs text-slate-400 mt-2">
            確認メールが受信できない場合は、迷惑メールフォルダを確認してください。
          </p>
        </div>

        <div className="space-y-2 text-sm text-slate-600 max-w-md mx-auto">
          <p>• パーツの準備ができましたら、お知らせします</p>
          <p>
            • ご不明点がありましたら
            <a
              href="https://panzer-blocks.com/contact-form/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline ml-1"
            >
              お問い合わせ
            </a>
            ください
          </p>
        </div>

        <div className="pt-4">
          <Link href="/">
            <Button onClick={resetForm} className="px-8">
              <Home className="w-4 h-4 mr-2" />
              トップページに戻る
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
