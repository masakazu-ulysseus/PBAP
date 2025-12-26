"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import Image from "next/image";
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { useApplication } from "@/lib/application-context";
import {
  Camera,
  Upload,
  Pencil,
  Trash2,
  Plus,
  Check,
  X,
  Loader2,
  ImageIcon,
  Undo2,
} from "lucide-react";

// react-konvaはSSR非対応のため動的インポート
const CanvasEditor = dynamic(
  () => import("@/components/canvas-editor").then((mod) => mod.CanvasEditor),
  { ssr: false, loading: () => <div className="p-4 text-center">読み込み中...</div> }
);

interface UploadedPhoto {
  id: string;
  originalFile: File;
  previewUrl: string;
  processedBlob?: Blob;
  lines: { points: number[]; stroke: string; strokeWidth: number }[];
  isEditing: boolean;
  editStageSize?: { width: number; height: number }; // 編集時のステージサイズを保持
}

interface StepPhotoPartsProps {
  onNext: () => void;
  onBack: () => void;
}

const MAX_PHOTOS = 10;
const MAX_SIZE = 1000;
const STROKE_COLOR = "#ff0000";
const STROKE_WIDTH = 4;

export function StepPhotoParts({ onNext, onBack }: StepPhotoPartsProps) {
  const { addPhotoPart, clearPhotoParts } = useApplication();
  const [photos, setPhotos] = useState<UploadedPhoto[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [editingPhotoId, setEditingPhotoId] = useState<string | null>(null);
  const [konvaImage, setKonvaImage] = useState<HTMLImageElement | null>(null);
  const [stageSize, setStageSize] = useState({ width: 0, height: 0 });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 画像をリサイズしてWebP形式に変換
  const processImage = useCallback(async (file: File): Promise<Blob> => {
    return new Promise((resolve, reject) => {
      const img = document.createElement("img");
      img.onload = () => {
        const canvas = document.createElement("canvas");
        let { width, height } = img;

        // 最大サイズにリサイズ
        if (width > MAX_SIZE || height > MAX_SIZE) {
          if (width > height) {
            height = (height / width) * MAX_SIZE;
            width = MAX_SIZE;
          } else {
            width = (width / height) * MAX_SIZE;
            height = MAX_SIZE;
          }
        }

        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("Canvas context not available"));
          return;
        }
        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(blob);
            } else {
              reject(new Error("Failed to create blob"));
            }
          },
          "image/webp",
          0.85
        );
      };
      img.onerror = () => reject(new Error("Failed to load image"));
      img.src = URL.createObjectURL(file);
    });
  }, []);

  // ファイル選択ハンドラ
  const handleFileSelect = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;

      const remainingSlots = MAX_PHOTOS - photos.length;
      if (remainingSlots <= 0) {
        alert(`画像は最大${MAX_PHOTOS}枚までです`);
        return;
      }

      setIsUploading(true);
      const filesToProcess = Array.from(files).slice(0, remainingSlots);

      try {
        const newPhotos: UploadedPhoto[] = await Promise.all(
          filesToProcess.map(async (file) => {
            const processedBlob = await processImage(file);
            const previewUrl = URL.createObjectURL(processedBlob);
            return {
              id: crypto.randomUUID(),
              originalFile: file,
              previewUrl,
              processedBlob,
              lines: [],
              isEditing: false,
            };
          })
        );

        setPhotos((prev) => [...prev, ...newPhotos]);
      } catch (error) {
        console.error("Error processing images:", error);
        alert("画像の処理中にエラーが発生しました");
      } finally {
        setIsUploading(false);
      }
    },
    [photos.length, processImage]
  );

  // 編集モード開始（オリジナル画像を表示して描画を重ねる）
  const startEditing = useCallback((photoId: string) => {
    setEditingPhotoId(photoId);
    const photo = photos.find((p) => p.id === photoId);
    if (photo && photo.processedBlob) {
      // オリジナル画像（processedBlob）から読み込む
      const originalUrl = URL.createObjectURL(photo.processedBlob);
      const img = document.createElement("img");
      img.onload = () => {
        setKonvaImage(img);
        // コンテナサイズに合わせてステージサイズを設定
        if (containerRef.current) {
          const containerWidth = containerRef.current.clientWidth - 32; // padding考慮
          const scale = Math.min(1, containerWidth / img.width);
          const newStageSize = {
            width: img.width * scale,
            height: img.height * scale,
          };
          setStageSize(newStageSize);
          // ステージサイズを写真オブジェクトに保存（後でスケーリングに使用）
          setPhotos((prev) =>
            prev.map((p) =>
              p.id === photoId ? { ...p, editStageSize: newStageSize } : p
            )
          );
        }
        // 一時URLは使用後に解放（imgオブジェクトが保持するので問題なし）
        URL.revokeObjectURL(originalUrl);
      };
      img.src = originalUrl;
    }
  }, [photos]);

  // 編集完了時にマーキング済み画像を生成してプレビューを更新
  const finishEditing = useCallback(async () => {
    if (!editingPhotoId) return;

    const photo = photos.find((p) => p.id === editingPhotoId);
    if (photo && photo.processedBlob && photo.lines.length > 0) {
      // 描画がある場合、オリジナル画像（processedBlob）にマーキングを重ねる
      const originalUrl = URL.createObjectURL(photo.processedBlob);
      const img = document.createElement("img");
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          URL.revokeObjectURL(originalUrl);
          return;
        }

        // 元画像を描画
        ctx.drawImage(img, 0, 0);

        // 描画線を重ねる（ステージサイズとオリジナルサイズの比率を計算）
        const scaleX = img.width / stageSize.width;
        const scaleY = img.height / stageSize.height;

        ctx.strokeStyle = STROKE_COLOR;
        ctx.lineWidth = STROKE_WIDTH * Math.max(scaleX, scaleY);
        ctx.lineCap = "round";
        ctx.lineJoin = "round";

        photo.lines.forEach((line) => {
          if (line.points.length < 4) return;
          ctx.beginPath();
          ctx.moveTo(line.points[0] * scaleX, line.points[1] * scaleY);
          for (let i = 2; i < line.points.length; i += 2) {
            ctx.lineTo(line.points[i] * scaleX, line.points[i + 1] * scaleY);
          }
          ctx.stroke();
        });

        // オリジナルURL解放
        URL.revokeObjectURL(originalUrl);

        // 新しいプレビューURLを生成
        canvas.toBlob(
          (blob) => {
            if (blob) {
              const newPreviewUrl = URL.createObjectURL(blob);
              // 古いプレビューURLを解放して新しいものに更新
              setPhotos((prev) =>
                prev.map((p) => {
                  if (p.id === editingPhotoId) {
                    URL.revokeObjectURL(p.previewUrl);
                    return { ...p, previewUrl: newPreviewUrl };
                  }
                  return p;
                })
              );
            }
          },
          "image/webp",
          0.85
        );
      };
      img.src = originalUrl;
    }

    setEditingPhotoId(null);
    setKonvaImage(null);
  }, [editingPhotoId, photos, stageSize]);

  // 写真削除
  const deletePhoto = useCallback((photoId: string) => {
    setPhotos((prev) => {
      const photo = prev.find((p) => p.id === photoId);
      if (photo) {
        URL.revokeObjectURL(photo.previewUrl);
      }
      return prev.filter((p) => p.id !== photoId);
    });
    if (editingPhotoId === photoId) {
      setEditingPhotoId(null);
      setKonvaImage(null);
    }
  }, [editingPhotoId]);

  // 描画クリア
  const clearLines = useCallback((photoId: string) => {
    setPhotos((prev) =>
      prev.map((photo) =>
        photo.id === photoId ? { ...photo, lines: [] } : photo
      )
    );
  }, []);

  // 編集キャンセル（保存せずに終了）
  const cancelEditing = useCallback(() => {
    setEditingPhotoId(null);
    setKonvaImage(null);
  }, []);

  // オリジナル画像にマーキングを重ねてBlobを生成
  const getMarkedImageBlob = useCallback(async (photo: UploadedPhoto): Promise<Blob | null> => {
    if (photo.lines.length === 0 || !photo.processedBlob || !photo.editStageSize) {
      // 描画がない、またはオリジナル画像・ステージサイズがない場合はnullを返す
      return null;
    }

    // オリジナル画像（processedBlob）に描画を重ねて新しいBlobを生成
    return new Promise((resolve, reject) => {
      const originalUrl = URL.createObjectURL(photo.processedBlob!);
      const img = document.createElement("img");
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          URL.revokeObjectURL(originalUrl);
          reject(new Error("Canvas context not available"));
          return;
        }

        // 元画像を描画
        ctx.drawImage(img, 0, 0);

        // 描画線を重ねる（ステージサイズとオリジナルサイズの比率を計算）
        const scaleX = img.width / photo.editStageSize!.width;
        const scaleY = img.height / photo.editStageSize!.height;

        ctx.strokeStyle = STROKE_COLOR;
        ctx.lineWidth = STROKE_WIDTH * Math.max(scaleX, scaleY);
        ctx.lineCap = "round";
        ctx.lineJoin = "round";

        photo.lines.forEach((line) => {
          if (line.points.length < 4) return;
          ctx.beginPath();
          ctx.moveTo(line.points[0] * scaleX, line.points[1] * scaleY);
          for (let i = 2; i < line.points.length; i += 2) {
            ctx.lineTo(line.points[i] * scaleX, line.points[i + 1] * scaleY);
          }
          ctx.stroke();
        });

        URL.revokeObjectURL(originalUrl);

        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(blob);
            } else {
              reject(new Error("Failed to create blob"));
            }
          },
          "image/webp",
          0.85
        );
      };
      img.onerror = () => {
        URL.revokeObjectURL(originalUrl);
        reject(new Error("Failed to load image"));
      };
      img.src = originalUrl;
    });
  }, []);

  // 次へ進む
  const handleNext = useCallback(async () => {
    if (photos.length === 0) {
      alert("少なくとも1枚の画像をアップロードしてください");
      return;
    }

    // コンテキストをクリアして新しいデータを追加
    clearPhotoParts();

    // 各写真をコンテキストに保存
    for (const photo of photos) {
      const markedBlob = await getMarkedImageBlob(photo);
      const previewUrl = markedBlob
        ? URL.createObjectURL(markedBlob)
        : photo.previewUrl;

      addPhotoPart({
        id: photo.id,
        originalBlob: photo.processedBlob!,
        markedBlob: markedBlob,
        previewUrl: previewUrl,
      });
    }

    onNext();
  }, [photos, onNext, getMarkedImageBlob, clearPhotoParts, addPhotoPart]);

  // クリーンアップ（アンマウント時のみ実行）
  useEffect(() => {
    return () => {
      photos.forEach((photo) => {
        URL.revokeObjectURL(photo.previewUrl);
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const editingPhoto = photos.find((p) => p.id === editingPhotoId);

  return (
    <Card>
      <CardHeader>
        <CardTitle>不足パーツの写真</CardTitle>
        <CardDescription>
          不足している部品を示す写真をアップロードしてください。
        </CardDescription>
      </CardHeader>
      <CardContent ref={containerRef}>
        {/* サンプル画像 */}
        <div className="mb-6 p-4 bg-slate-50 rounded-lg border">
          <p className="text-sm text-slate-600 mb-2">
            以下のサンプルを参考に、不足部品がわかるように撮影してください<br />
            <span className="text-xs text-slate-500">（アップロード後に、🖊️ボタンから画像に印を付けることができます。）</span>
          </p>
          <ol className="text-sm text-slate-600 mb-3 list-decimal list-inside space-y-1">
            <li>製品付属の組立説明書を開きます</li>
            <li>不足している部品が含まれる組立番号のページを開きます</li>
            <li>組立番号の部品一覧の中から、不足している部品に○印をつけ、不足数を横に記載します<br />
              <span className="text-xs text-slate-500 ml-5">※ 印のみで個数がない場合は、１つと判断します</span>
            </li>
          </ol>
          <div className="relative w-full max-w-md mx-auto aspect-square">
            <Image
              src="/images/lost_parts1-768x756.webp"
              alt="サンプル画像"
              fill
              className="object-contain rounded"
            />
          </div>
        </div>

        {/* アップロードボタン */}
        <div className="flex gap-3 mb-6">
          <Button
            type="button"
            variant="outline"
            className="flex-1"
            onClick={() => fileInputRef.current?.click()}
            disabled={photos.length >= MAX_PHOTOS || isUploading}
          >
            {isUploading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Upload className="w-4 h-4 mr-2" />
            )}
            アップロード
          </Button>
          <Button
            type="button"
            variant="outline"
            className="flex-1"
            onClick={() => cameraInputRef.current?.click()}
            disabled={photos.length >= MAX_PHOTOS || isUploading}
          >
            <Camera className="w-4 h-4 mr-2" />
            カメラで撮影
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files)}
          />
          <input
            ref={cameraInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files)}
          />
        </div>

        {/* アップロード枚数表示 */}
        <p className="text-sm text-slate-500 mb-4">
          アップロード済み: {photos.length} / {MAX_PHOTOS}枚
        </p>

        {/* 編集モード */}
        {editingPhotoId && editingPhoto && konvaImage && (
          <div className="mb-6 p-4 bg-slate-100 rounded-lg">
            <p className="text-sm font-medium mb-3">
              不足部品に印を付けてください（フリーハンドで描画）
            </p>
            <div className="border rounded bg-white overflow-hidden touch-none mb-3">
              <CanvasEditor
                image={konvaImage}
                width={stageSize.width}
                height={stageSize.height}
                lines={editingPhoto.lines}
                onLinesChange={(newLines) => {
                  setPhotos((prev) =>
                    prev.map((photo) =>
                      photo.id === editingPhotoId
                        ? { ...photo, lines: newLines }
                        : photo
                    )
                  );
                }}
                strokeColor={STROKE_COLOR}
                strokeWidth={STROKE_WIDTH}
              />
            </div>
            <div className="grid grid-cols-2 gap-2 sm:flex sm:justify-end">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => clearLines(editingPhotoId)}
              >
                <X className="w-4 h-4 mr-1" />
                クリア
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={cancelEditing}
              >
                <Undo2 className="w-4 h-4 mr-1" />
                キャンセル
              </Button>
              <Button
                type="button"
                variant="default"
                size="sm"
                onClick={finishEditing}
                className="col-span-2"
              >
                <Check className="w-4 h-4 mr-1" />
                保存して終了
              </Button>
            </div>
          </div>
        )}

        {/* アップロード済み写真一覧 */}
        {photos.length > 0 && !editingPhotoId && (
          <div className="space-y-4 mb-6">
            {photos.map((photo, index) => (
              <div
                key={photo.id}
                className="p-3 bg-slate-50 rounded-lg border"
              >
                <div className="relative w-full aspect-square max-w-md mx-auto mb-3">
                  <Image
                    src={photo.previewUrl}
                    alt={`アップロード画像 ${index + 1}`}
                    fill
                    className="object-contain rounded"
                  />
                  {photo.lines.length > 0 && (
                    <div className="absolute top-2 right-2 bg-green-500 text-white text-xs px-2 py-1 rounded">
                      印付き
                    </div>
                  )}
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">画像 {index + 1}</p>
                    <p className="text-xs text-slate-500">
                      {photo.lines.length > 0
                        ? "印が付けられています"
                        : "印を付けてください"}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => startEditing(photo.id)}
                    >
                      <Pencil className="w-4 h-4 mr-1" />
                      編集
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => deletePhoto(photo.id)}
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 空の状態 */}
        {photos.length === 0 && (
          <div className="text-center py-8 border-2 border-dashed rounded-lg mb-6">
            <ImageIcon className="w-12 h-12 mx-auto text-slate-300 mb-2" />
            <p className="text-slate-500">まだ画像がアップロードされていません</p>
          </div>
        )}

        {/* 追加ボタン */}
        {photos.length > 0 && photos.length < MAX_PHOTOS && !editingPhotoId && (
          <Button
            type="button"
            variant="outline"
            className="w-full mb-6"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            <Plus className="w-4 h-4 mr-2" />
            画像を追加
          </Button>
        )}

        {/* ナビゲーション */}
        <div className="pt-4 flex gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={onBack}
            className="flex-1"
          >
            戻る
          </Button>
          <Button
            type="button"
            onClick={handleNext}
            className="flex-1"
            disabled={photos.length === 0}
          >
            次へ進む
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
