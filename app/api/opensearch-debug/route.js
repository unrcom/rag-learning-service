import { opensearchClient } from "@/app/lib/opensearch";
import { titanEmbeddings } from "@/app/lib/embeddings";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const client = await opensearchClient.initialize();
    const debug = [];

    // 1. インデックス内の全ドキュメントを確認
    debug.push("🔍 Step 1: Checking all documents in index...");
    const allDocs = await client.search({
      index: "documents",
      body: {
        query: { match_all: {} },
        size: 10,
        _source: { exclude: ["vector_field"] },
      },
    });

    const docCount = allDocs.body.hits.hits.length;
    debug.push("📄 Found " + docCount + " documents total");

    // 2. ドキュメントの構造確認
    const sampleDoc = allDocs.body.hits.hits[0];
    if (sampleDoc) {
      debug.push("📋 Sample document structure:");
      debug.push("   - ID: " + sampleDoc._id);
      debug.push("   - Fields: " + Object.keys(sampleDoc._source).join(", "));
      debug.push("   - Title: " + sampleDoc._source.title);
      debug.push(
        "   - Text: " +
          (sampleDoc._source.text?.substring(0, 100) || "No text") +
          "..."
      );
    }

    // 3. 手動でベクトル検索テスト
    debug.push("🔍 Step 2: Testing vector search with low threshold...");

    const testQuery = "人工知能";
    const queryVector = await titanEmbeddings.embedText(testQuery);
    debug.push(
      "🔤 Generated query vector: " + queryVector.length + " dimensions"
    );

    // 非常に低いスコア閾値で検索
    const vectorResults = await client.search({
      index: "documents",
      body: {
        size: 5,
        min_score: 0.0,
        query: {
          knn: {
            vector_field: {
              vector: queryVector,
              k: 5,
            },
          },
        },
        _source: {
          exclude: ["vector_field"],
        },
      },
    });

    const vectorHitCount = vectorResults.body.hits.hits.length;
    debug.push("🔍 Vector search results: " + vectorHitCount + " hits");

    if (vectorHitCount > 0) {
      vectorResults.body.hits.hits.forEach((hit, index) => {
        debug.push(
          "   Result " +
            (index + 1) +
            ": Score=" +
            hit._score.toFixed(4) +
            ', Title="' +
            hit._source.title +
            '"'
        );
      });
    }

    // 4. 通常のテキスト検索もテスト
    debug.push("🔍 Step 3: Testing regular text search...");
    const textResults = await client.search({
      index: "documents",
      body: {
        query: {
          multi_match: {
            query: testQuery,
            fields: ["text", "title"],
            type: "best_fields",
          },
        },
        size: 5,
      },
    });

    const textHitCount = textResults.body.hits.hits.length;
    debug.push("📝 Text search results: " + textHitCount + " hits");

    if (textHitCount > 0) {
      textResults.body.hits.hits.forEach((hit, index) => {
        debug.push(
          "   Text Result " +
            (index + 1) +
            ": Score=" +
            hit._score.toFixed(4) +
            ', Title="' +
            hit._source.title +
            '"'
        );
      });
    }

    // 5. 実際のRAGクエリテスト
    debug.push("🔍 Step 4: Testing actual RAG queries...");
    const ragTestQueries = [
      "人工知能でコンテンツを作る技術について教えて",
      "外部データを使って回答精度を上げる方法",
    ];

    for (const ragQuery of ragTestQueries) {
      try {
        const results = await opensearchClient.searchByText(
          "documents",
          ragQuery,
          3,
          0.3
        ); // 低いスコア閾値
        debug.push(
          '🔍 RAG Query: "' +
            ragQuery.substring(0, 30) +
            '..." → ' +
            results.length +
            " results"
        );

        if (results.length > 0) {
          results.forEach((result, idx) => {
            debug.push(
              "   RAG Result " +
                (idx + 1) +
                ": Score=" +
                result.score.toFixed(4) +
                ', Title="' +
                result.source.title +
                '"'
            );
          });
        }
      } catch (error) {
        debug.push("❌ RAG Query failed: " + error.message);
      }
    }

    return NextResponse.json({
      success: true,
      message: "Detailed OpenSearch debugging completed",
      debug_log: debug,
      summary: {
        total_documents: allDocs.body.hits.total.value,
        vector_search_hits: vectorHitCount,
        text_search_hits: textHitCount,
        sample_titles: allDocs.body.hits.hits
          .slice(0, 3)
          .map((hit) => hit._source.title),
      },
    });
  } catch (error) {
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
