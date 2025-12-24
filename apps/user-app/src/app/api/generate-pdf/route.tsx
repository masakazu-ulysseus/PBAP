import { NextRequest, NextResponse } from "next/server";
import {
  Page,
  Text,
  View,
  Document,
  StyleSheet,
  Font,
  Image as PDFImage,
  renderToBuffer,
} from "@react-pdf/renderer";
import fs from "fs";
import path from "path";
import sharp from "sharp";
import { createChildLogger, generateRequestId } from "@/lib/logger";

// フォントを登録
Font.register({
  family: "NotoSansJP",
  src: path.join(process.cwd(), "public/fonts/NotoSansJP-Regular.ttf"),
});

Font.register({
  family: "NotoSansJP-Bold",
  src: path.join(process.cwd(), "public/fonts/NotoSansJP-Bold.ttf"),
});

interface PdfData {
  taskId: string;
  applicationNumber?: number; // 申請番号（10000から始まる連番）
  applicantName: string;
  applicantEmail?: string | null;
  productName: string;
  purchaseDate: string;
  purchaseStore: string;
  parts: Array<{
    assemblyNumber: string;
    partName: string;
    quantity: number;
    partImageUrl?: string | null;
    imageBase64?: string | null;
  }>;
}

// スタイル定義
const styles = StyleSheet.create({
  page: {
    flexDirection: "column",
    padding: 30,
    fontFamily: "NotoSansJP",
    fontSize: 10,
  },
  header: {
    marginBottom: 20,
  },
  logo: {
    fontSize: 24,
    fontFamily: "NotoSansJP-Bold",
    color: "#454e5f",
    textAlign: "center",
    marginBottom: 5,
  },
  applicationId: {
    fontSize: 16,
    textAlign: "center",
    marginBottom: 10,
  },
  separator: {
    borderBottom: "1 solid #454e5f",
    marginBottom: 15,
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: "bold",
    marginBottom: 8,
    fontFamily: "NotoSansJP-Bold",
  },
  infoRow: {
    flexDirection: "row",
    marginBottom: 4,
  },
  infoLabel: {
    width: 80,
    fontWeight: "bold",
  },
  infoValue: {
    flex: 1,
  },
  table: {
    width: "100%",
  },
  tableHeader: {
    flexDirection: "row",
    backgroundColor: "#f0f0f0",
    borderBottom: "1 solid #000",
  },
  tableRow: {
    flexDirection: "row",
    borderBottom: "1 solid #ddd",
  },
  tableCell: {
    padding: 5,
    fontSize: 9,
  },
  imageCell: {
    width: 60,
    alignItems: "center",
  },
  assemblyCell: {
    width: 80,
    alignItems: "center",
  },
  partCell: {
    flex: 1,
  },
  quantityCell: {
    width: 60,
    alignItems: "center",
  },
  footer: {
    position: "absolute",
    bottom: 30,
    left: 30,
    right: 30,
    textAlign: "center",
    fontSize: 8,
    color: "#666",
  },
});

// 部品名から数字のみを抽出する関数
const extractPartNumber = (partName: string): string => {
  // 正規表現で数字のみを抽出
  const match = partName.match(/\d+/);
  return match ? match[0] : "";
};

// PDFドキュメントコンポーネント
const MyDocument = ({ data }: { data: PdfData }) => (
  <Document>
    <Page size="A4" style={styles.page}>
      <View style={styles.header}>
        <Text style={styles.logo}>PANZER BLOCKS</Text>
        <Text style={styles.applicationId}>
          申請番号: {data.applicationNumber || data.taskId}
        </Text>
      </View>

      <View style={styles.separator} />

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>申請者情報</Text>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>お名前:</Text>
          <Text style={styles.infoValue}>{data.applicantName}</Text>
        </View>
        {data.applicantEmail && (
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>メール:</Text>
            <Text style={styles.infoValue}>{data.applicantEmail}</Text>
          </View>
        )}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>製品情報</Text>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>製品名:</Text>
          <Text style={styles.infoValue}>{data.productName}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>購入日:</Text>
          <Text style={styles.infoValue}>{data.purchaseDate}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>購入店舗:</Text>
          <Text style={styles.infoValue}>{data.purchaseStore}</Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>
          申請パーツ ({data.parts.length}点)
        </Text>

        {/* テーブルヘッダー */}
        <View style={styles.tableHeader}>
          <View style={[styles.tableCell, styles.imageCell]}>
            <Text>画像</Text>
          </View>
          <View style={[styles.tableCell, styles.assemblyCell]}>
            <Text>組立番号</Text>
          </View>
          <View style={[styles.tableCell, styles.partCell]}>
            <Text>部品番号</Text>
          </View>
          <View style={[styles.tableCell, styles.quantityCell]}>
            <Text>数量</Text>
          </View>
        </View>

        {/* テーブルデータ */}
        {data.parts.map((part, index) => (
          <View key={index} style={styles.tableRow}>
            <View style={[styles.tableCell, styles.imageCell]}>
              {part.imageBase64 ? (
                <PDFImage
                  src={part.imageBase64}
                  style={{ width: 40, height: 40, objectFit: "contain" }}
                />
              ) : (
                <Text>-</Text>
              )}
            </View>
            <View style={[styles.tableCell, styles.assemblyCell]}>
              <Text>{part.assemblyNumber}</Text>
            </View>
            <View style={[styles.tableCell, styles.partCell]}>
              <Text>{extractPartNumber(part.partName || "")}</Text>
            </View>
            <View style={[styles.tableCell, styles.quantityCell]}>
              <Text>{part.quantity}</Text>
            </View>
          </View>
        ))}
      </View>

      {/* 注意書き */}
      <View style={{ marginTop: 20, paddingHorizontal: 30 }}>
        <Text style={{ fontSize: 9, color: "#666", textAlign: "center" }}>
          パーツの準備ができましたら、
          {data.applicantEmail || "ご登録のメールアドレス"}宛にご連絡致します。
        </Text>
      </View>

      <View style={styles.footer}>
        <Text>Copyright © 2025 Ulysseus Co., Ltd.</Text>
      </View>
    </Page>
  </Document>
);

export async function POST(request: NextRequest) {
  const requestId = generateRequestId();
  const logger = createChildLogger("generate-pdf", { requestId });

  try {
    const data: PdfData = await request.json();

    logger.info(
      { taskId: data.taskId, partsCount: data.parts.length },
      "Starting PDF generation",
    );

    // 画像をダウンロードしてbase64に変換
    logger.debug({ partsCount: data.parts.length }, "Processing parts with images");
    const processedParts = await Promise.all(
      data.parts.map(async (part, index) => {
        logger.debug(
          { partIndex: index, partImageUrl: part.partImageUrl, assemblyNumber: part.assemblyNumber },
          "Processing part",
        );
        if (part.partImageUrl) {
          try {
            logger.debug({ url: part.partImageUrl }, "Fetching image");
            const response = await fetch(part.partImageUrl);
            logger.debug({ status: response.status }, "Image fetch response");

            if (!response.ok) {
              throw new Error(
                `HTTP ${response.status}: ${response.statusText}`,
              );
            }

            // WebPをPNG/JPEGに変換する必要がある
            const contentType = response.headers.get("content-type") || "";
            logger.debug({ contentType }, "Image content type");

            const arrayBuffer = await response.arrayBuffer();
            logger.debug({ size: arrayBuffer.byteLength }, "Image buffer size");

            // Sharpを使ってWebPをPNGに変換
            let base64: string;
            if (contentType.includes("webp")) {
              logger.debug("Converting WebP to PNG");
              const pngBuffer = await sharp(arrayBuffer)
                .png({ quality: 90 })
                .toBuffer();
              base64 = Buffer.from(pngBuffer).toString("base64");
              logger.debug({ size: pngBuffer.length }, "Converted to PNG");
            } else {
              base64 = Buffer.from(arrayBuffer).toString("base64");
            }

            // PDF用の画像データ（PNGまたはJPEG）
            const imageData = `data:image/${contentType.includes("webp") ? "png" : "jpeg"};base64,${base64}`;
            logger.debug(
              { imageDataLength: imageData.length },
              "Generated base64 image",
            );

            return {
              ...part,
              imageBase64: imageData,
            };
          } catch (error) {
            logger.error(
              { url: part.partImageUrl, error: error instanceof Error ? error.message : "Unknown error" },
              "Failed to fetch image",
            );
            return { ...part, imageBase64: null };
          }
        }
        return { ...part, imageBase64: null };
      }),
    );

    logger.debug(
      {
        processedParts: processedParts.map((p) => ({
          assemblyNumber: p.assemblyNumber,
          hasImage: !!p.imageBase64,
          imageLength: p.imageBase64?.length || 0,
        })),
      },
      "Parts processing completed",
    );

    const pdfBuffer = await renderToBuffer(
      <MyDocument data={{ ...data, parts: processedParts }} />,
    );

    // ファイルに一時保存
    const tempPath = `/tmp/application_${data.taskId}.pdf`;
    fs.writeFileSync(tempPath, pdfBuffer);

    // Create a readable stream from the file
    const fileStream = fs.createReadStream(tempPath);

    logger.info(
      { taskId: data.taskId, pdfSize: pdfBuffer.length },
      "PDF generation completed successfully",
    );

    // Return the stream as response
    return new Response(fileStream as unknown as BodyInit, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="application_${data.taskId}.pdf"`,
      },
    });
  } catch (error) {
    logger.error(
      { error: error instanceof Error ? error.message : "Unknown error", stack: error instanceof Error ? error.stack : undefined },
      "PDF generation failed",
    );
    return NextResponse.json(
      { error: "Failed to generate PDF" },
      { status: 500 },
    );
  }
}
