"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { useApplication } from "@/lib/application-context";
import {
  getAssemblyPages,
  getAssemblyImages,
  getPartsForAssemblyImage,
} from "@/lib/supabase";
import type { AssemblyPage, AssemblyImage } from "@/types/database";
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Minus,
  Trash2,
  Loader2,
  Package,
  CheckCircle,
  MousePointer2,
  HelpCircle,
  ExternalLink,
} from "lucide-react";

interface StepPartsProps {
  onNext: () => void;
  onBack: () => void;
  debugMode?: boolean;
}

interface PartWithQuantity {
  partId: string;
  partName: string | null;
  partImageUrl: string | null;
  assemblyImageId: string;
  assemblyNumber: string;
  defaultQuantity: number;
}

export function StepParts({
  onNext,
  onBack,
  debugMode = false,
}: StepPartsProps) {
  const { formData, addSelectedPart, removeSelectedPart, updatePartQuantity } =
    useApplication();
  const [pages, setPages] = useState<AssemblyPage[]>([]);
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [assemblyImages, setAssemblyImages] = useState<AssemblyImage[]>([]);
  const [selectedAssemblyImage, setSelectedAssemblyImage] =
    useState<AssemblyImage | null>(null);
  const [parts, setParts] = useState<PartWithQuantity[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingImages, setLoadingImages] = useState(false);
  const [loadingParts, setLoadingParts] = useState(false);
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const [noPartsDialogOpen, setNoPartsDialogOpen] = useState(false);
  const imageContainerRef = useRef<HTMLDivElement>(null);

  // クロスフェードアニメーション用の状態
  const [isFading, setIsFading] = useState(false);

  // 組立ページ一覧の取得
  useEffect(() => {
    const fetchPages = async () => {
      if (!formData.purchaseInfo.productId) return;
      try {
        const pagesData = await getAssemblyPages(
          formData.purchaseInfo.productId,
        );
        setPages(pagesData);
      } catch (error) {
        console.error("Error fetching pages:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchPages();
  }, [formData.purchaseInfo.productId]);

  // 現在のページの組立番号画像を取得
  useEffect(() => {
    const fetchAssemblyImages = async () => {
      if (pages.length === 0) return;
      const currentPage = pages[currentPageIndex];
      if (!currentPage) return;

      setLoadingImages(true);
      setSelectedAssemblyImage(null);
      setParts([]);
      try {
        const images = await getAssemblyImages(currentPage.id);
        setAssemblyImages(images);
      } catch (error) {
        console.error("Error fetching assembly images:", error);
      } finally {
        setLoadingImages(false);
      }
    };
    fetchAssemblyImages();
  }, [pages, currentPageIndex]);

  // 画像サイズの更新
  useEffect(() => {
    const updateSize = () => {
      if (imageContainerRef.current) {
        const rect = imageContainerRef.current.getBoundingClientRect();
        setImageSize({ width: rect.width, height: rect.height });
      }
    };

    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, [currentPageIndex, pages]);

  // ページ切り替えハンドラー（次のページ）
  const handleNextPage = useCallback(() => {
    if (currentPageIndex >= pages.length - 1) return;
    setIsFading(true);
    setCurrentPageIndex((prev) => prev + 1);
    setSelectedAssemblyImage(null);
    setParts([]);
    // アニメーション終了後にリセット
    setTimeout(() => setIsFading(false), 600);
  }, [currentPageIndex, pages.length]);

  // ページ切り替えハンドラー（前のページ）
  const handlePrevPage = useCallback(() => {
    if (currentPageIndex <= 0) return;
    setIsFading(true);
    setCurrentPageIndex((prev) => prev - 1);
    setSelectedAssemblyImage(null);
    setParts([]);
    // アニメーション終了後にリセット
    setTimeout(() => setIsFading(false), 600);
  }, [currentPageIndex]);

  // 選択された組立番号の部品を取得
  const fetchParts = useCallback(async (assemblyImage: AssemblyImage) => {
    setLoadingParts(true);
    try {
      const partsData = await getPartsForAssemblyImage(assemblyImage.id);
      const formattedParts: PartWithQuantity[] = partsData
        .filter((item) => item.part !== null)
        .map((item) => ({
          partId: item.part!.id,
          partName: item.part!.name,
          partImageUrl: item.part!.parts_url,
          assemblyImageId: assemblyImage.id,
          assemblyNumber: assemblyImage.assembly_number,
          defaultQuantity: item.quantity,
        }));
      setParts(formattedParts);
    } catch (error) {
      console.error("Error fetching parts:", error);
    } finally {
      setLoadingParts(false);
    }
  }, []);

  // 組立番号画像が選択された時
  const handleSelectAssemblyImage = (image: AssemblyImage) => {
    setSelectedAssemblyImage(image);
    fetchParts(image);
  };

  // 画像クリック時の処理
  const handleImageClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (
      !imageContainerRef.current ||
      naturalSize.width === 0 ||
      naturalSize.height === 0
    )
      return;

    const imgElement = imageContainerRef.current.querySelector("img");
    if (!imgElement) return;

    const imgRect = imgElement.getBoundingClientRect();
    const containerRect = imageContainerRef.current.getBoundingClientRect();

    // 画像内のクリック座標（画像の表示位置を考慮）
    const clickX = e.clientX - imgRect.left;
    const clickY = e.clientY - imgRect.top;

    // 表示画像の実際のサイズ
    const displayWidth = imgRect.width;
    const displayHeight = imgRect.height;

    // 表示サイズと元画像サイズの比率を計算
    const scaleX = naturalSize.width / displayWidth;
    const scaleY = naturalSize.height / displayHeight;

    // クリック座標を元画像の座標に変換
    const originalX = clickX * scaleX;
    const originalY = clickY * scaleY;

    // デバッグ情報
    console.log("Click Debug:", {
      clickPosition: { x: clickX, y: clickY },
      displaySize: { width: displayWidth, height: displayHeight },
      naturalSize,
      scale: { x: scaleX, y: scaleY },
      originalPosition: { x: originalX, y: originalY },
      offsets: {
        containerToImage: {
          x: imgRect.left - containerRect.left,
          y: imgRect.top - containerRect.top,
        },
      },
    });

    // どの組立番号領域に該当するかチェック
    for (const image of assemblyImages) {
      if (
        image.region_x !== null &&
        image.region_y !== null &&
        image.region_width !== null &&
        image.region_height !== null
      ) {
        const x1 = image.region_x;
        const y1 = image.region_y;
        const x2 = x1 + image.region_width;
        const y2 = y1 + image.region_height;

        // 少し余裕を持たせて判定（誤差吸収のため±5px）
        if (
          originalX >= x1 - 5 &&
          originalX <= x2 + 5 &&
          originalY >= y1 - 5 &&
          originalY <= y2 + 5
        ) {
          handleSelectAssemblyImage(image);
          return;
        }
      }
    }
  };

  // 部品の追加
  const handleAddPart = (part: PartWithQuantity) => {
    addSelectedPart({
      partId: part.partId,
      partName: part.partName,
      partImageUrl: part.partImageUrl,
      assemblyImageId: part.assemblyImageId,
      assemblyNumber: part.assemblyNumber,
      quantity: 1,
    });
  };

  // 選択済み部品の数量を取得
  const getSelectedQuantity = (partId: string, assemblyImageId: string) => {
    const selected = formData.selectedParts.find(
      (p) => p.partId === partId && p.assemblyImageId === assemblyImageId,
    );
    return selected?.quantity || 0;
  };

  // 座標を表示用に変換する関数（コンテナ幅に合わせて縮小）
  const getDisplayRegion = (image: AssemblyImage) => {
    if (
      image.region_x === null ||
      image.region_y === null ||
      image.region_width === null ||
      image.region_height === null ||
      naturalSize.width === 0
    ) {
      return null;
    }

    // 縮小率を計算（コンテナ幅 / 元画像幅）
    // imageSize.widthは画像の表示幅（CSSでwidth:100%にしているので、コンテナ幅と同じ）
    const scale = imageSize.width > 0 ? imageSize.width / naturalSize.width : 1;

    // 縮小後の座標を計算
    const finalLeft = image.region_x * scale;
    const finalTop = image.region_y * scale;

    return {
      left: finalLeft,
      top: finalTop,
      width: image.region_width * scale,
      height: image.region_height * scale,
    };
  };

  const currentPage = pages[currentPageIndex];

  // 座標データを持つ組立画像があるかチェック
  const hasRegionData = assemblyImages.some(
    (img) => img.region_x !== null && img.region_y !== null,
  );

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

  if (pages.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Package className="w-12 h-12 mx-auto text-slate-300" />
          <p className="mt-4 text-slate-500">
            この製品の組立説明書データがありません
          </p>
          <div className="pt-4 flex gap-3 justify-center">
            <Button variant="outline" onClick={onBack}>
              戻る
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>不足パーツの選択</CardTitle>
        <CardDescription>
          {hasRegionData
            ? "組立説明書の画像をクリックして、不足しているパーツの組立番号を選択してください"
            : "組立説明書のページをめくって、不足しているパーツを選択してください"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* ページナビゲーション */}
        <div className="flex items-center justify-between bg-slate-50 rounded-lg p-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePrevPage}
            disabled={currentPageIndex === 0}
          >
            <ChevronLeft className="w-5 h-5" />
            前のページ
          </Button>
          <span className="text-sm font-medium">
            ページ {currentPage?.page_number || "-"} / {pages.length}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={handleNextPage}
            disabled={currentPageIndex === pages.length - 1}
          >
            次のページ
            <ChevronRight className="w-5 h-5" />
          </Button>
        </div>

        {/* 組立ページ画像 */}
        <div className="border rounded-lg overflow-hidden bg-white">
          {currentPage?.image_url ? (
            <div
              ref={imageContainerRef}
              className={`relative cursor-crosshair ${isFading ? "page-crossfade" : ""}`}
              onClick={hasRegionData ? handleImageClick : undefined}
            >
              <div style={{ width: "100%", position: "relative" }}>
                <img
                  src={currentPage.image_url}
                  alt={`ページ ${currentPage.page_number}`}
                  style={{
                    width: "100%",
                    height: "auto",
                  }}
                  onLoad={(e) => {
                    const img = e.target as HTMLImageElement;
                    setNaturalSize({
                      width: img.naturalWidth,
                      height: img.naturalHeight,
                    });
                    // 画像読み込み後にサイズを再計算
                    setImageSize({
                      width: img.clientWidth,
                      height: img.clientHeight,
                    });
                  }}
                />
              </div>

              {/* クリック可能領域のオーバーレイ */}
              {hasRegionData &&
                assemblyImages.map((image) => {
                  const region = getDisplayRegion(image);
                  if (!region) return null;

                  const isSelected = selectedAssemblyImage?.id === image.id;

                  return (
                    <div
                      key={image.id}
                      className={`absolute border-2 transition-all cursor-pointer ${
                        isSelected
                          ? "border-blue-500 bg-blue-500/20"
                          : debugMode
                            ? "border-red-500 bg-red-100/30"
                            : "border-transparent hover:border-blue-300 hover:bg-blue-100/30"
                      }`}
                      style={{
                        left: region.left,
                        top: region.top,
                        width: region.width,
                        height: region.height,
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectAssemblyImage(image);
                      }}
                    >
                      <Badge
                        className={`absolute -bottom-3 -right-3 text-xs ${
                          isSelected ? "bg-blue-500" : "bg-slate-600"
                        }`}
                      >
                        {image.assembly_number}
                      </Badge>
                    </div>
                  );
                })}

              {/* クリックヒント */}
              {hasRegionData && !selectedAssemblyImage && (
                <div className="absolute bottom-2 left-2 right-2 bg-black/70 text-white text-xs p-2 rounded flex items-center gap-2">
                  <MousePointer2 className="w-4 h-4" />
                  組立番号内にある不足部品をクリックしてください
                </div>
              )}
            </div>
          ) : (
            <div className="aspect-[3/4] flex items-center justify-center bg-slate-100">
              <p className="text-slate-400">画像がありません</p>
            </div>
          )}
        </div>

        {/* 座標データがない場合のフォールバック：組立番号グリッド */}
        {!hasRegionData && (
          <div className="space-y-3">
            <p className="text-sm font-medium text-slate-700">組立番号を選択</p>
            {loadingImages ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
              </div>
            ) : assemblyImages.length === 0 ? (
              <p className="text-sm text-slate-500 py-4">
                このページには組立番号がありません
              </p>
            ) : (
              <div className="grid grid-cols-4 md:grid-cols-6 gap-2">
                {assemblyImages.map((image) => (
                  <button
                    key={image.id}
                    onClick={() => handleSelectAssemblyImage(image)}
                    className={`relative aspect-square border-2 rounded-lg overflow-hidden transition-all ${
                      selectedAssemblyImage?.id === image.id
                        ? "border-blue-500 ring-2 ring-blue-200"
                        : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    {image.image_url ? (
                      <Image
                        src={image.image_url}
                        alt={`組立番号 ${image.assembly_number}`}
                        fill
                        className="object-contain p-1"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-slate-100">
                        <span className="text-xs text-slate-400">
                          {image.assembly_number}
                        </span>
                      </div>
                    )}
                    <Badge
                      className="absolute bottom-1 right-1 text-xs"
                      variant={
                        selectedAssemblyImage?.id === image.id
                          ? "default"
                          : "secondary"
                      }
                    >
                      {image.assembly_number}
                    </Badge>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 選択された組立番号画像 */}
        {selectedAssemblyImage && (
          <div className="border-t pt-4">
            <p className="text-sm font-medium text-slate-700 mb-3">
              選択された組立番号: {selectedAssemblyImage.assembly_number}
            </p>
            <div className="flex justify-center mb-4">
              <div className="relative border-2 border-blue-500 rounded-lg overflow-hidden bg-white max-w-md">
                {selectedAssemblyImage.image_url ? (
                  <Image
                    src={selectedAssemblyImage.image_url}
                    alt={`組立番号 ${selectedAssemblyImage.assembly_number}`}
                    width={400}
                    height={300}
                    className="w-full h-auto object-contain"
                  />
                ) : (
                  <div className="w-full h-48 flex items-center justify-center bg-slate-100">
                    <span className="text-slate-400">画像がありません</span>
                  </div>
                )}
                <Badge className="absolute top-2 left-2 bg-blue-500">
                  組立番号 {selectedAssemblyImage.assembly_number}
                </Badge>
              </div>
            </div>
          </div>
        )}

        {/* 部品一覧 */}
        {selectedAssemblyImage && (
          <div className="border-t pt-4">
            <p className="text-sm font-medium text-slate-700 mb-3">
              組立番号 {selectedAssemblyImage.assembly_number} のパーツを選択
            </p>
            {loadingParts ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
              </div>
            ) : parts.length === 0 ? (
              <p className="text-sm text-slate-500">部品データがありません</p>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {parts.map((part) => {
                  const quantity = getSelectedQuantity(
                    part.partId,
                    part.assemblyImageId,
                  );
                  return (
                    <div
                      key={`${part.partId}-${part.assemblyImageId}`}
                      className={`border rounded-lg p-2 ${
                        quantity > 0 ? "border-blue-500 bg-blue-50" : ""
                      }`}
                    >
                      <div className="relative aspect-square mb-2 bg-white rounded overflow-hidden">
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
                      <p className="text-xs text-slate-600 truncate mb-2">
                        {part.partName || "パーツ"}
                      </p>
                      {quantity === 0 ? (
                        <Button
                          size="sm"
                          variant="outline"
                          className="w-full"
                          onClick={() => handleAddPart(part)}
                        >
                          <Plus className="w-4 h-4 mr-1" />
                          追加
                        </Button>
                      ) : (
                        <div className="flex items-center justify-between">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-8 w-8 p-0"
                            onClick={() =>
                              updatePartQuantity(
                                part.partId,
                                part.assemblyImageId,
                                quantity - 1,
                              )
                            }
                          >
                            <Minus className="w-4 h-4" />
                          </Button>
                          <span className="font-medium">{quantity}</span>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-8 w-8 p-0"
                            onClick={() =>
                              updatePartQuantity(
                                part.partId,
                                part.assemblyImageId,
                                quantity + 1,
                              )
                            }
                          >
                            <Plus className="w-4 h-4" />
                          </Button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* 選択済みパーツ一覧 */}
        {formData.selectedParts.length > 0 && (
          <div className="border-t pt-4">
            <p className="text-sm font-medium text-slate-700 mb-2">
              選択済みパーツ ({formData.selectedParts.length}点)
            </p>
            <div className="flex flex-wrap items-center gap-1">
              {formData.selectedParts.map((part, index) => (
                <span
                  key={`${part.partId}-${part.assemblyImageId}`}
                  className="flex items-center"
                >
                  <Badge
                    variant="secondary"
                    className="flex items-center gap-1"
                  >
                    組立 {part.assemblyNumber}-{part.partName || "パーツ"} x
                    {part.quantity}
                    <button
                      onClick={() =>
                        removeSelectedPart(part.partId, part.assemblyImageId)
                      }
                      className="ml-1 hover:text-red-500"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </Badge>
                  {index < formData.selectedParts.length - 1 && (
                    <span className="text-slate-400 mx-1">,</span>
                  )}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* ナビゲーションボタン */}
        <div className="pt-4 space-y-3">
          {/* パーツが選択されている場合のアクションボタン */}
          {formData.selectedParts.length > 0 && (
            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setSelectedAssemblyImage(null);
                  setParts([]);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                className="flex-1"
              >
                <Plus className="w-4 h-4 mr-2" />
                他のパーツを追加
              </Button>
              <Button onClick={onNext} className="flex-1">
                <CheckCircle className="w-4 h-4 mr-2" />
                パーツの選択終了・確認
              </Button>
            </div>
          )}
          {/* 戻るボタン */}
          <Button
            type="button"
            variant="ghost"
            onClick={onBack}
            className="w-full"
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            購入情報の入力に戻る
          </Button>
          {/* 不足部品がない場合のボタン */}
          <Button
            type="button"
            variant="ghost"
            onClick={() => setNoPartsDialogOpen(true)}
            className="w-full text-slate-500"
          >
            <HelpCircle className="w-4 h-4 mr-1" />
            表示内容に不足部品は無かった
          </Button>
        </div>

        {/* 不足部品がない場合のダイアログ */}
        <Dialog open={noPartsDialogOpen} onOpenChange={setNoPartsDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>不足部品が存在しない場合</DialogTitle>
              <DialogDescription className="pt-2">
                表示されている部品の中に不足部品が存在しない場合は、お問い合わせフォームからお問い合わせください。
              </DialogDescription>
            </DialogHeader>
            <div className="pt-4 space-y-3">
              <Button
                className="w-full"
                onClick={() => {
                  window.open(
                    "https://panzer-blocks.com/contact-form/",
                    "_blank",
                  );
                }}
              >
                <ExternalLink className="w-4 h-4 mr-2" />
                お問い合わせフォーム
              </Button>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => setNoPartsDialogOpen(false)}
              >
                <span className="text-slate-500">もどる</span>
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
