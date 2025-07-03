import { opensearchClient } from "@/app/lib/opensearch";
import { titanEmbeddings } from "@/app/lib/embeddings";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    console.log("🚀 Starting full RAG system test...");

    // 1. サンプルドキュメント準備
    const sampleDocuments = [
      {
        text: "生成AI（Generative AI）は、機械学習モデルを使用して新しいコンテンツを作成する人工知能の分野です。テキスト、画像、音声、動画などを生成できます。",
        title: "生成AI概要",
        source: "ai_textbook",
        chunk_id: "gen_ai_001",
        metadata: {
          document_type: "educational",
          category: "artificial_intelligence",
          difficulty: "beginner",
        },
      },
      {
        text: "RAG（Retrieval-Augmented Generation）は、外部の知識ベースから関連情報を検索し、その情報を使ってより正確で具体的な回答を生成する手法です。",
        title: "RAG手法の説明",
        source: "ai_textbook",
        chunk_id: "rag_001",
        metadata: {
          document_type: "educational",
          category: "machine_learning",
          difficulty: "intermediate",
        },
      },
      {
        text: "ベクトルデータベースは、高次元ベクトルデータを効率的に格納・検索するためのデータベースです。類似度検索やセマンティック検索に使用されます。",
        title: "ベクトルデータベース",
        source: "ai_textbook",
        chunk_id: "vector_db_001",
        metadata: {
          document_type: "educational",
          category: "database",
          difficulty: "intermediate",
        },
      },
    ];

    // 2. ドキュメントをベクトル埋め込み付きで追加
    console.log("📝 Adding documents with embeddings...");
    const addResults = [];

    for (const doc of sampleDocuments) {
      const result = await opensearchClient.addTextDocument("documents", doc);
      addResults.push(result._id);
      // 各ドキュメント間で少し待機
      await new Promise((resolve) => setTimeout(resolve, 500));
    }

    // 3. インデックス処理完了を待機
    console.log("⏳ Waiting for indexing to complete...");
    await new Promise((resolve) => setTimeout(resolve, 3000));

    // 4. セマンティック検索テスト
    const testQueries = [
      "人工知能でコンテンツを作る技術について教えて",
      "外部データを使って回答精度を上げる方法",
      "高次元データの検索方法",
    ];

    const searchResults = {};
    for (const query of testQueries) {
      console.log(`🔍 Testing query: "\${query}"`);
      const results = await opensearchClient.searchByText(
        "documents",
        query,
        2
        // 2,
        // 0.6
      );
      searchResults[query] = results;
    }

    // 5. 類似度計算テスト
    const similarity = await titanEmbeddings.calculateSimilarity(
      testQueries[0],
      sampleDocuments[0].text
    );

    return NextResponse.json({
      success: true,
      message: "Full RAG system test completed successfully!",
      test_results: {
        documents_added: addResults.length,
        document_ids: addResults,
        semantic_search_results: Object.keys(searchResults).map((query) => ({
          query,
          results_count: searchResults[query].length,
          top_result: searchResults[query][0]
            ? {
                title: searchResults[query][0].source.title,
                score: searchResults[query][0].score,
                text_preview:
                  searchResults[query][0].source.text.substring(0, 100) + "...",
              }
            : null,
        })),
        similarity_test: {
          text1: testQueries[0].substring(0, 50) + "...",
          text2: sampleDocuments[0].text.substring(0, 50) + "...",
          similarity_score: similarity,
        },
      },
    });
  } catch (error) {
    console.error("❌ RAG system test failed:", error);

    return NextResponse.json(
      {
        success: false,
        error: error.message,
        stack: error.stack,
      },
      { status: 500 }
    );
  }
}
