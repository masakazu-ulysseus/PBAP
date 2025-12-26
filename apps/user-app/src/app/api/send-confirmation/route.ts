import { NextRequest, NextResponse } from "next/server";
import nodemailer from "nodemailer";
import { createChildLogger, generateRequestId } from "@/lib/logger";

// SMTPトランスポーターを作成
const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST,
  port: Number(process.env.SMTP_PORT) || 587,
  secure: process.env.SMTP_SECURE === "true", // 465の場合true
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASSWORD,
  },
});

export async function POST(request: NextRequest) {
  const requestId = generateRequestId();
  const apiLogger = createChildLogger("send-confirmation-api", { requestId });

  try {
    const {
      email,
      recipientName,
      taskId,
      applicationNumber, // 申請番号を追加
      productName,
      partsCount,
      parts,
      purchaseDate,
      purchaseStore,
      userMemo,
    } = await request.json();

    apiLogger.info(
      {
        taskId,
        applicationNumber,
        recipientEmail: email,
        recipientName,
        productName,
        partsCount,
      },
      "Email confirmation request received",
    );

    // SMTP設定がない場合はスキップ
    if (
      !process.env.SMTP_HOST ||
      !process.env.SMTP_USER ||
      !process.env.SMTP_PASSWORD
    ) {
      apiLogger.warn("SMTP not configured, skipping email");
      return NextResponse.json({ success: true, skipped: true });
    }

    // PDFを生成
    let pdfBuffer: Buffer | null = null;
    const pdfStartTime = Date.now();
    try {
      apiLogger.debug("Starting PDF generation");
      const pdfUrl = `${process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3001"}/api/generate-pdf`;
      apiLogger.debug({ pdfUrl }, "PDF generation URL");

      const pdfResponse = await fetch(pdfUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          taskId,
          applicationNumber, // 申請番号を追加
          applicantName: recipientName,
          applicantEmail: email,
          productName,
          purchaseDate,
          purchaseStore,
          parts,
          userMemo,
        }),
        signal: AbortSignal.timeout(60000), // 60秒タイムアウト
      });

      const pdfDuration = Date.now() - pdfStartTime;

      if (pdfResponse.ok) {
        pdfBuffer = Buffer.from(await pdfResponse.arrayBuffer());
        apiLogger.info(
          {
            size: pdfBuffer.length,
            duration: pdfDuration,
          },
          "PDF generated successfully",
        );
      } else {
        const errorText = await pdfResponse.text();
        apiLogger.error(
          {
            status: pdfResponse.status,
            statusText: pdfResponse.statusText,
            responseBody: errorText,
            duration: pdfDuration,
          },
          "PDF generation failed",
        );
      }
    } catch (pdfError) {
      apiLogger.error(
        {
          error: pdfError instanceof Error ? pdfError.message : "Unknown error",
          stack: pdfError instanceof Error ? pdfError.stack : "No stack trace",
        },
        "PDF generation error",
      );
      // PDF生成失敗してもメールは送信
    }

    apiLogger.debug(
      {
        hasPdfAttachment: pdfBuffer !== null,
        pdfSize: pdfBuffer?.length || 0,
      },
      "Preparing email with attachments",
    );

    const mailOptions = {
      from: `"PANZER BLOCKS" <${process.env.SMTP_FROM || process.env.SMTP_USER}>`,
      to: email,
      subject: "パーツ申請を受け付けました - PANZER BLOCKS",
      html: `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body { font-family: sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .header { background: #454e5f; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; background: #f8fafc; }
            .info-box { background: white; border: 1px solid #e2e8f0; padding: 15px; margin: 15px 0; border-radius: 8px; }
            .footer { text-align: center; padding: 20px; color: #64748b; font-size: 12px; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>PANZER BLOCKS</h1>
            </div>
            <div class="content">
              <p>${recipientName} 様</p>
              <p>パーツ申請を受け付けました。</p>

              <div class="info-box">
                <p><strong>申請番号:</strong> ${applicationNumber}</p>
                <p><strong>製品名:</strong> ${productName}</p>
                <p><strong>申請パーツ数:</strong> ${partsCount}点</p>
              </div>

              <p>申請内容の詳細をPDFにまとめましたので、ご確認ください。</p>
              <p>内容を確認し、ご連絡致します。</p>

              <p>ご不明な点がございましたら、<a href="https://panzer-blocks.com/contact-form/" style="color: #0066cc;">こちら</a>からお問い合わせください。</p>
            </div>
            <div class="footer">
              <p>Copyright © 2025 Ulysseus Co., Ltd.</p>
              <p>このメールは自動送信されています。返信はできません。</p>
            </div>
          </div>
        </body>
        </html>
      `,
      attachments: pdfBuffer
        ? [
            {
              filename: `申請書_${applicationNumber}.pdf`,
              content: pdfBuffer,
              contentType: "application/pdf",
            },
          ]
        : [],
    };

    const emailStartTime = Date.now();
    apiLogger.debug(
      {
        attachmentCount: mailOptions.attachments.length,
      },
      "Sending email",
    );

    await transporter.sendMail(mailOptions);
    const emailDuration = Date.now() - emailStartTime;

    apiLogger.info(
      {
        duration: emailDuration,
        hasPdfAttachment: pdfBuffer !== null,
      },
      "Email sent successfully",
    );

    return NextResponse.json({ success: true });
  } catch (error) {
    apiLogger.error(
      {
        error: error instanceof Error ? error.message : "Unknown error",
        stack: error instanceof Error ? error.stack : "No stack trace",
      },
      "Error sending email",
    );
    return NextResponse.json(
      { error: "Failed to send email" },
      { status: 500 },
    );
  }
}
