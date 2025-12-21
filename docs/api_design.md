# API設計書

## 1. 概要
本ドキュメントは、**ユーザー向けシステム (Next.js)** が提供するAPIエンドポイントについて記述します。
管理者向け機能は Python アプリケーション (Streamlit) として独立し、Supabase SDK を介して直接データベース/ストレージを操作するため、REST API定義からは除外します。

## 2. 共通仕様
*   **Base URL**: `/api/v1` (Next.js App Router Server Actions / Route Handlers)
*   **Content-Type**: `application/json`

## 3. エンドポイント一覧 (ユーザー向け)

### 3.1 商品情報取得
*   **GET** `/products`
*   **概要**: 商品一覧または検索結果を取得する。
*   **Query Params**:
    *   `q`: 検索キーワード (商品名など)
*   **Response**:
    ```json
    [
      {
        "itemId": "prod_123",
        "name": "Tank Model A",
        "series_name": "WWII Series"
      }
    ]
    ```

### 3.2 組立ページ一覧取得
*   **GET** `/products/{productId}/assembly-pages`
*   **概要**: 指定商品の組立ページ一覧（および紐づく組立番号画像・部品）を取得する。
*   **Response**:
    ```json
    {
      "productId": "prod_123",
      "pages": [
        {
          "pageId": "page_001",
          "pageNumber": 1,
          "imageUrl": "https://[project-ref].supabase.co/storage/v1/object/public/assembly-pages/page_001/main.webp",
          "assemblyImages": [
            {
              "imageId": "img_001",
              "assemblyNumber": "1",
              "url": "https://[project-ref].supabase.co/storage/v1/object/public/assembly-pages/page_001/images/img_001.webp",
              "parts": [
                {
                  "partId": "part_a",
                  "name": null,
                  "partsUrl": "https://[project-ref].supabase.co/storage/v1/object/public/assembly-pages/page_001/images/img_001/parts/part_a.webp"
                }
              ]
            }
          ]
        }
      ]
    }
    ```

### 3.3 申請送信
*   **POST** `/tasks`
*   **概要**: 不足部品申請を送信し、申請タスクを登録する。
*   **Request Body**:
    ```json
    {
      "userInfo": {
        "zipCode": "123-4567",
        "address": "Tokyo...",
        "email": "user@example.com",
        "name": "Taro Yamada",
        "phone": "090-0000-0000"
      },
      "purchaseInfo": {
        "productName": "Tank Model A",
        "store": "Toy Store",
        "date": "2024-01-01",
        "warrantyCode": "CODE123"
      },
      "parts": [
        { "imageId": "img_001", "partId": "part_a", "quantity": 1 }
      ]
    }
    ```
*   **Response**:
    *   201 Created: `{ "taskId": "task_xyz" }`
    *   400 Bad Request: バリデーションエラー

## 4. エラーハンドリング
*   **400 Bad Request**: 入力値不正
*   **404 Not Found**: リソース不在
*   **500 Internal Server Error**: サーバー内部エラー
