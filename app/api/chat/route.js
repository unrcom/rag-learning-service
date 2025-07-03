import { getCurrentAPI } from "@/app/config/api";
import { NextResponse } from "next/server";

export async function POST(request) {
  try {
    const { message } = await request.json();

    if (!message?.trim()) {
      return NextResponse.json(
        {
          success: false,
          error: "メッセージが空です",
        },
        { status: 400 }
      );
    }

    console.log(`💬 User query: "${message}"`);

    const apiConfig = getCurrentAPI();

    // V2（FastAPI）を使用する場合
    if (apiConfig.baseUrl) {
      console.log("🔄 Forwarding to FastAPI...");

      const fastApiResponse = await fetch(
        `${apiConfig.baseUrl}${apiConfig.chatEndpoint}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ message }),
        }
      );

      if (!fastApiResponse.ok) {
        throw new Error(`FastAPI Error: ${fastApiResponse.status}`);
      }

      const result = await fastApiResponse.json();
      return NextResponse.json(result);
    }

    // V1（既存のNext.js API）を使用する場合
    // 既存のコードをここに保持...
    const { opensearchClient } = await import("@/app/lib/opensearch");
    const { generateGuardedResponse } = await import("@/app/lib/bedrock");

    console.log("🔄 Using Next.js API...");

    // 1. RAG検索で関連文書を取得
    const searchResults = await opensearchClient.searchByText(
      "aws_summit_sessions",
      message,
      3
    );

    console.log(`🔍 Found ${searchResults.length} relevant documents`);

    // 2. コンテキストを構築
    let context = "";
    const sources = [];

    if (searchResults.length > 0) {
      context = "以下の情報を参考にして回答してください：\n\n";

      searchResults.forEach((result, index) => {
        context += `【参考資料${index + 1}】\n`;
        context += `タイトル: ${result.source.title}\n`;

        if (result.source.abstract) {
          context += `概要: ${result.source.abstract}\n`;
        }

        if (result.source.speakers && result.source.speakers.length > 0) {
          const speakerNames = result.source.speakers
            .map((speaker) => `${speaker.name}（${speaker.company}）`)
            .join(", ");
          context += `講演者: ${speakerNames}\n`;
        }

        if (result.source.track) {
          context += `トラック: ${result.source.track}\n`;
        }

        if (result.source.date && result.source.start_time) {
          context += `開催日時: ${result.source.date} ${result.source.start_time}\n`;
        }

        context += "\n";

        sources.push({
          title: result.source.title,
          score: result.score.toFixed(4),
        });
      });
    } else {
      context =
        "関連する参考資料が見つかりませんでした。一般的な知識で回答してください。\n\n";
    }

    // 3. LLMプロンプト構築
    const prompt = `${context}

質問: ${message}

以下の点を守って日本語で回答してください：
- 必ず日本語で回答する
- 丁寧で分かりやすい表現を使う
- 参考資料がある場合は、その内容を基に回答する
- 参考資料がない場合は、一般的な知識で回答する

回答:`;

    console.log(
      `🤖 Generating response with context from ${searchResults.length} sources`
    );

    // 4. ガードレール付きでLLM回答生成
    const llmResult = await generateGuardedResponse(prompt);

    // 5. レスポンスの正規化
    let finalResponse;
    if (typeof llmResult === "string") {
      finalResponse = llmResult;
    } else if (llmResult && typeof llmResult === "object") {
      finalResponse =
        llmResult.guardedContent ||
        llmResult.originalContent ||
        llmResult.response ||
        "エラー: 回答を取得できませんでした";
    } else {
      finalResponse = "エラー: 無効な回答形式です";
    }

    return NextResponse.json({
      success: true,
      response: finalResponse,
      sources: sources,
      context_used: searchResults.length > 0,
      debug: {
        api_version: "v1 (Next.js)",
        search_results_count: searchResults.length,
        guardrail_applied: llmResult?.guardrailApplied || false,
      },
    });
  } catch (error) {
    console.error("❌ Chat API error:", error);

    return NextResponse.json(
      {
        success: false,
        error: error.message || "不明なエラーが発生しました",
      },
      { status: 500 }
    );
  }
}
