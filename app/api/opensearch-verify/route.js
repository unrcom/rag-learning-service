import { opensearchClient } from "@/app/lib/opensearch";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    console.log("🔍 Verifying OpenSearch setup with real data...");

    // 1. 現在のドキュメント数確認
    const client = await opensearchClient.initialize();
    const countResult = await client.count({ index: "documents" });
    console.log(`📊 Current document count: \${countResult.body.count}`);

    // 2. 全てのドキュメントを取得
    const allDocs = await client.search({
      index: "documents",
      body: {
        query: { match_all: {} },
        size: 10,
        _source: { exclude: ["vector_field"] },
      },
    });

    console.log(`📄 Retrieved \${allDocs.body.hits.hits.length} documents`);

    // 3. ベクトル検索テスト
    const testVector = Array(1536)
      .fill(0)
      .map(() => Math.random() - 0.5);
    const searchResults = await opensearchClient.vectorSearch(
      "documents",
      testVector,
      3,
      0.0
    );

    console.log(`🔍 Vector search found \${searchResults.length} results`);

    return NextResponse.json({
      success: true,
      message: "OpenSearch verification completed successfully!",
      current_status: {
        document_count: countResult.body.count,
        vector_search_results: searchResults.length,
        sample_documents: allDocs.body.hits.hits.map((hit) => ({
          id: hit._id,
          score: hit._score,
          title: hit._source.title,
          text: hit._source.text?.substring(0, 100) + "...",
          metadata: hit._source.metadata,
        })),
      },
    });
  } catch (error) {
    console.error("❌ Verification failed:", error);
    return NextResponse.json(
      {
        success: false,
        error: error.message,
      },
      { status: 500 }
    );
  }
}
