"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Package,
  ClipboardList,
  Send,
  CheckCircle,
  ArrowRight,
} from "lucide-react";

export default function Home() {
  const [showWarrantyCodeImage, setShowWarrantyCodeImage] = useState(false);

  return (
    <div className="min-h-screen bg-white">
      {/* Hero Section */}
      <main>
        <section className="relative min-h-[100vh] flex items-center justify-center overflow-hidden">
          {/* Background Image */}
          <div className="absolute inset-0">
            <Image
              src="/images/hero-blocks.webp"
              alt="PANZER BLOCKS 組立シーン"
              fill
              className="object-cover"
              priority
              style={{
                transform: "scale(1.05)",
                transformStyle: "preserve-3d",
              }}
            />
            {/* Dark Overlay for text readability */}
            <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-black/10 to-transparent"></div>
            {/* Gradient overlay at bottom */}
            <div className="absolute inset-0 bg-gradient-to-t from-white/60 via-white/40 to-transparent translate-y-20"></div>
          </div>

          {/* Header with Logo and Navigation */}
          <div className="absolute top-3 left-8 right-8 z-20 flex items-center justify-between">
            <Image
              src="/images/logo.svg"
              alt="PANZER BLOCKS"
              width={240}
              height={53}
              className="h-14 w-auto"
              priority
            />
            <nav className="flex items-center gap-6">
              <Link
                href="https://panzer-blocks.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-white hover:text-white/80 transition-colors drop-shadow-lg"
              >
                公式サイト
              </Link>
              <Link
                href="https://shop.panzer-blocks.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-white hover:text-white/80 transition-colors drop-shadow-lg"
              >
                公式ショップ
              </Link>
            </nav>
          </div>

          {/* Background Pattern - subtle */}
          <div className="absolute inset-0 bg-gradient-to-br from-white/20 via-transparent to-transparent/50">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_0%,_rgba(0,0,0,0.3)_100%)] opacity-30"></div>
          </div>

          {/* Decorative Elements */}
          <div className="absolute top-20 left-10 w-72 h-72 bg-blue-50/20 rounded-full filter blur-3xl animate-pulse"></div>
          <div className="absolute bottom-20 right-10 w-96 h-96 bg-slate-100/20 rounded-full filter blur-3xl animate-pulse delay-1000"></div>

          <div className="relative z-10 container mx-auto px-4 text-center">
            <div className="max-w-4xl mx-auto">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 bg-gradient-to-r from-amber-500/90 to-orange-600/90 text-white px-4 py-2 rounded-full text-sm font-medium mb-6 shadow-lg backdrop-blur-sm">
                公式パーツ申請サービス
              </div>

              {/* Main Heading */}
              <h1 className="text-5xl md:text-7xl font-bold text-gray-900 mb-6 tracking-tight drop-shadow-lg">
                <span className="bg-gradient-to-r from-gray-900 to-black bg-clip-text text-transparent">
                  PANZER BLOCKS
                </span>
                <br />
                <span className="text-3xl md:text-5xl text-black">
                  パーツ申請サービス
                </span>
              </h1>

              {/* Description */}
              <p className="text-lg md:text-xl text-black mb-8 max-w-2xl mx-auto leading-relaxed drop-shadow-lg">
                スムーズで簡単に不足パーツの申請が行えます。
              </p>

              {/* CTA Buttons */}
              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
                <Link href="/apply">
                  <Button
                    size="lg"
                    className="group relative px-8 py-4 text-lg bg-gradient-to-r from-primary to-slate-700 hover:from-slate-700 hover:to-slate-800 text-white shadow-xl hover:shadow-2xl transition-all duration-300 transform hover:scale-105"
                  >
                    申請を開始する
                    <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Process Section */}
        <section className="py-20 bg-gradient-to-b from-slate-50 to-white">
          <div className="container mx-auto px-4">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
                かんたん4ステップで
                <br className="sm:hidden" />
                申請完了
              </h2>
              <p className="text-lg text-slate-600 max-w-2xl mx-auto">
                シンプルな入力フォームで、スムーズにパーツを申請できます
              </p>
            </div>

            <div className="grid md:grid-cols-4 gap-8 max-w-6xl mx-auto">
              {/* Step 1 */}
              <div className="relative group">
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-10">
                  <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-full flex items-center justify-center text-sm font-bold shadow-lg">
                    1
                  </div>
                </div>
                <Card className="h-full pt-8 border-0 shadow-lg group-hover:shadow-xl transition-all duration-300 bg-white/80 backdrop-blur-sm">
                  <CardContent className="text-center p-6">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-blue-100 to-blue-200 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                      <ClipboardList className="w-8 h-8 text-blue-600" />
                    </div>
                    <h3 className="font-bold text-slate-900 mb-2">購入情報</h3>
                    <p className="text-sm text-slate-600">
                      製品と保証コードを入力
                    </p>
                  </CardContent>
                </Card>
                {/* Connector Line */}
                <div className="hidden md:block absolute top-1/2 -right-4 w-8 h-0.5 bg-gradient-to-r from-transparent to-slate-200"></div>
              </div>

              {/* Step 2 */}
              <div className="relative group">
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-10">
                  <div className="w-8 h-8 bg-gradient-to-r from-green-600 to-green-700 text-white rounded-full flex items-center justify-center text-sm font-bold shadow-lg">
                    2
                  </div>
                </div>
                <Card className="h-full pt-8 border-0 shadow-lg group-hover:shadow-xl transition-all duration-300 bg-white/80 backdrop-blur-sm">
                  <CardContent className="text-center p-6">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-green-100 to-green-200 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                      <Package className="w-8 h-8 text-green-600" />
                    </div>
                    <h3 className="font-bold text-slate-900 mb-2">
                      パーツ選択
                    </h3>
                    <p className="text-sm text-slate-600">不足パーツを選択</p>
                  </CardContent>
                </Card>
                {/* Connector Line */}
                <div className="hidden md:block absolute top-1/2 -right-4 w-8 h-0.5 bg-gradient-to-r from-transparent to-slate-200"></div>
              </div>

              {/* Step 3 */}
              <div className="relative group">
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-10">
                  <div className="w-8 h-8 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-full flex items-center justify-center text-sm font-bold shadow-lg">
                    3
                  </div>
                </div>
                <Card className="h-full pt-8 border-0 shadow-lg group-hover:shadow-xl transition-all duration-300 bg-white/80 backdrop-blur-sm">
                  <CardContent className="text-center p-6">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-purple-100 to-purple-200 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                      <Send className="w-8 h-8 text-purple-600" />
                    </div>
                    <h3 className="font-bold text-slate-900 mb-2">
                      送付先情報
                    </h3>
                    <p className="text-sm text-slate-600">
                      お届け先の情報を入力
                    </p>
                  </CardContent>
                </Card>
                {/* Connector Line */}
                <div className="hidden md:block absolute top-1/2 -right-4 w-8 h-0.5 bg-gradient-to-r from-transparent to-slate-200"></div>
              </div>

              {/* Step 4 */}
              <div className="relative group">
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-10">
                  <div className="w-8 h-8 bg-gradient-to-r from-orange-600 to-orange-700 text-white rounded-full flex items-center justify-center text-sm font-bold shadow-lg">
                    4
                  </div>
                </div>
                <Card className="h-full pt-8 border-0 shadow-lg group-hover:shadow-xl transition-all duration-300 bg-white/80 backdrop-blur-sm">
                  <CardContent className="text-center p-6">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-orange-100 to-orange-200 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                      <CheckCircle className="w-8 h-8 text-orange-600" />
                    </div>
                    <h3 className="font-bold text-slate-900 mb-2">申請完了</h3>
                    <p className="text-sm text-slate-600">内容を確認して送信</p>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </section>

        {/* Info Section */}
        <section className="py-20 bg-white">
          <div className="container mx-auto px-4">
            <div className="max-w-4xl mx-auto">
              <Card className="border-0 shadow-xl bg-gradient-to-br from-slate-50 to-white">
                <CardHeader className="text-center pb-6">
                  <CardTitle className="text-2xl font-bold text-slate-900">
                    ご利用にあたって
                  </CardTitle>
                  <div className="w-16 h-1 bg-gradient-to-r from-blue-600 to-blue-700 mx-auto rounded-full"></div>
                </CardHeader>
                <CardContent className="space-y-6 p-8">
                  <div className="flex items-start gap-4">
                    <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-1">
                      <span className="w-2 h-2 bg-red-600 rounded-full"></span>
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-900 mb-1">
                        パンツァーブロックス製品ご購入者様専用
                      </h4>
                      <p className="text-slate-600">
                        販売店での購入、パンツァーブロックス公式サイトでの購入が確認出来ないお客様は、本サービスの対象外となります。
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-4">
                    <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mt-1">
                      <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-900 mb-1">
                        部品保証コードが必要です
                      </h4>
                      <p className="text-slate-600">
                        申請には製品に付属の
                        <button
                          onClick={() => setShowWarrantyCodeImage(true)}
                          className="text-blue-600 font-medium hover:text-blue-700 underline ml-1"
                        >
                          部品保証コード（6桁）
                        </button>
                        が必要です。事前にご準備ください。
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-4">
                    <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0 mt-1">
                      <span className="w-2 h-2 bg-green-600 rounded-full"></span>
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-900 mb-1">
                        送料無料
                      </h4>
                      <p className="text-slate-600">
                        すべてのパーツ発送は無料です。
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
          <div className="container mx-auto px-4 text-center">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-8">
              必要なパーツを今すぐ申請
            </h2>
            <Link href="/apply">
              <Button
                size="lg"
                className="group bg-white text-primary hover:bg-slate-100 px-8 py-4 text-lg shadow-xl hover:shadow-2xl transition-all duration-300 transform hover:scale-105"
              >
                申請を開始する
                <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 text-white py-8">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-4 md:mb-0">
              <Image
                src="/images/logo.svg"
                alt="PANZER BLOCKS"
                width={200}
                height={44}
                className="h-10 w-auto opacity-80"
              />
            </div>
            <div className="flex flex-col md:flex-row items-center gap-4 md:gap-8">
              <nav className="flex flex-col md:flex-row items-center gap-4 md:gap-6 text-sm">
                <Link
                  href="https://panzer-blocks.com/about/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-400 hover:text-white transition-colors"
                >
                  サイト利用について
                </Link>
                <Link
                  href="https://panzer-blocks.com/about/privacy-policy/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-400 hover:text-white transition-colors"
                >
                  個人情報保護方針
                </Link>
                <Link
                  href="https://panzer-blocks.com/about/companyprofile/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-400 hover:text-white transition-colors"
                >
                  運営会社
                </Link>
              </nav>
              <p className="text-sm text-slate-400">
                Copyright © 2025 Ulysseus Co., Ltd.
              </p>
            </div>
          </div>
        </div>
      </footer>

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
    </div>
  );
}
