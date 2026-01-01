"use client";

import Image from "next/image";
import { useSearchParams } from "next/navigation";
import { Suspense, use } from "react";
import { useApplication } from "@/lib/application-context";
import { StepShipping } from "@/components/steps/step-shipping";
import { StepPurchase, OTHER_PRODUCT_ID } from "@/components/steps/step-purchase";
import { StepParts } from "@/components/steps/step-parts";
import { StepPhotoParts } from "@/components/steps/step-photo-parts";
import { StepConfirm } from "@/components/steps/step-confirm";
import { StepComplete } from "@/components/steps/step-complete";
import { CheckCircle } from "lucide-react";
import Link from "next/link";

// 通常フロー用のステップ
const normalSteps = [
  { number: 1, title: "購入情報" },
  { number: 2, title: "パーツ選択" },
  { number: 3, title: "送付先情報" },
  { number: 4, title: "確認" },
];

// その他フロー用のステップ
const otherSteps = [
  { number: 1, title: "購入情報" },
  { number: 2, title: "パーツ写真" },
  { number: 3, title: "送付先情報" },
  { number: 4, title: "確認" },
];

function ApplyPageContent() {
  const { currentStep, setCurrentStep, formData } = useApplication();
  const searchParams = useSearchParams();
  const debugMode = searchParams.get("debug") === "true";

  // 「その他」フローかどうかを判定
  const isOtherFlow = formData.purchaseInfo.productId === OTHER_PRODUCT_ID;
  const steps = isOtherFlow ? otherSteps : normalSteps;

  const handleNext = () => {
    setCurrentStep(currentStep + 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleBack = () => {
    setCurrentStep(currentStep - 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleComplete = () => {
    setCurrentStep(5);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      {/* Header */}
      <header className="border-b bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/">
            <Image
              src="/images/logo.svg"
              alt="PANZER BLOCKS"
              width={150}
              height={34}
              className="h-8 w-auto"
            />
          </Link>
          <span className="text-sm text-slate-700 font-medium">
            PANZER BLOCKS パーツ申請サービス
          </span>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-2xl">
        {/* Step Indicator */}
        {currentStep <= 4 && (
          <div className="mb-8">
            <div className="flex items-center justify-between">
              {steps.map((step, index) => (
                <div key={step.number} className="flex items-center">
                  <div className="flex flex-col items-center">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                        currentStep > step.number
                          ? "bg-green-500 text-white"
                          : currentStep === step.number
                            ? "bg-blue-500 text-white"
                            : "bg-slate-200 text-slate-500"
                      }`}
                    >
                      {currentStep > step.number ? (
                        <CheckCircle className="w-5 h-5" />
                      ) : (
                        step.number
                      )}
                    </div>
                    <span
                      className={`mt-2 text-xs ${
                        currentStep >= step.number
                          ? "text-slate-700"
                          : "text-slate-400"
                      }`}
                    >
                      {step.title}
                    </span>
                  </div>
                  {index < steps.length - 1 && (
                    <div
                      className={`h-0.5 w-full mx-2 transition-colors ${
                        currentStep > step.number
                          ? "bg-green-500"
                          : "bg-slate-200"
                      }`}
                      style={{ minWidth: "40px" }}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step Content */}
        {currentStep === 1 && (
          <StepPurchase onNext={handleNext} />
        )}
        {currentStep === 2 && (
          isOtherFlow ? (
            <StepPhotoParts onNext={handleNext} onBack={handleBack} />
          ) : (
            <StepParts
              onNext={handleNext}
              onBack={handleBack}
              debugMode={debugMode}
            />
          )
        )}
        {currentStep === 3 && <StepShipping onNext={handleNext} onBack={handleBack} />}
        {currentStep === 4 && (
          <StepConfirm onComplete={handleComplete} onBack={handleBack} />
        )}
        {currentStep === 5 && <StepComplete />}
      </main>

      {/* Footer */}
      <footer className="border-t bg-white mt-auto">
        <div className="container mx-auto px-4 py-6 text-center text-sm text-slate-500">
          Copyright © 2025 Ulysseus Co., Ltd.
        </div>
      </footer>
    </div>
  );
}

export default function ApplyPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="text-slate-500">読み込み中...</div>
      </div>
    }>
      <ApplyPageContent />
    </Suspense>
  );
}
