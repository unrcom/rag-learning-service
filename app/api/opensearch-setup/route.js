import { opensearchClient } from "@/app/lib/opensearch";
import { NextResponse } from "next/server";

export async function GET(request) {
  try {
    // URL パラメータでインデックスタイプを指定
    const url = new URL(request.url);
    const indexType = url.searchParams.get("type") || "general";

    console.log(`🔧 Setting up OpenSearch index, type: \${indexType}`);

    if (indexType === "aws-summit") {
      // AWS Summit専用インデックス作成
      const result = await opensearchClient.createAwsSummitIndex();
      return NextResponse.json({
        success: true,
        message: "AWS Summit index created successfully",
        index: "aws_summit_sessions",
        type: "aws-summit",
        result,
      });
    } else {
      // 既存の汎用インデックス作成
      const result = await opensearchClient.createVectorIndex();
      return NextResponse.json({
        success: true,
        message: "General index created successfully",
        index: "documents",
        type: "general",
        result,
      });
    }
  } catch (error) {
    console.error("❌ Setup error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error.message,
        details: error.stack,
      },
      { status: 500 }
    );
  }
}
