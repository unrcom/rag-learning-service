import {
  BedrockRuntimeClient,
  InvokeModelCommand,
} from "@aws-sdk/client-bedrock-runtime";

// Bedrockクライアント初期化
const bedrockClient = new BedrockRuntimeClient({
  region: process.env.AWS_REGION || "ap-northeast-1",
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  },
});

// Claude 3 Haikuでテキスト生成
export async function generateResponse(prompt, systemPrompt = "") {
  try {
    const messages = [
      {
        role: "user",
        content: prompt,
      },
    ];

    // システムプロンプトがある場合は追加
    const requestBody = {
      anthropic_version: "bedrock-2023-05-31",
      max_tokens: 1000,
      temperature: 0.1,
      messages: messages,
    };

    if (systemPrompt) {
      requestBody.system = systemPrompt;
    }

    const command = new InvokeModelCommand({
      modelId: "anthropic.claude-v2:1",
      contentType: "application/json",
      accept: "application/json",
      body: JSON.stringify(requestBody),
    });

    const response = await bedrockClient.send(command);
    const responseBody = JSON.parse(new TextDecoder().decode(response.body));

    return {
      success: true,
      content: responseBody.content[0].text,
      usage: responseBody.usage,
    };
  } catch (error) {
    console.error("Bedrock API Error:", error);
    return {
      success: false,
      error: error.message,
      content: null,
    };
  }
}

// 接続テスト用関数
export async function testBedrockConnection() {
  const testPrompt = "こんにちは！接続テストです。簡単に挨拶してください。";

  console.log("=== Bedrock接続テスト開始 ===");
  const result = await generateResponse(testPrompt);

  if (result.success) {
    console.log("✅ Bedrock接続成功！");
    console.log("回答:", result.content);
    console.log("使用量:", result.usage);
  } else {
    console.log("❌ Bedrock接続失敗");
    console.log("エラー:", result.error);
  }

  return result;
}

// ガードレール付きレスポンス生成
export async function generateGuardedResponse(prompt, systemPrompt = "") {
  const { CostAwarenessGuardrail } = await import("./guardrails.js");
  const guardrail = new CostAwarenessGuardrail();

  // 基本レスポンス生成
  const baseResponse = await generateResponse(prompt, systemPrompt);

  if (!baseResponse.success) {
    return baseResponse;
  }

  // ガードレール適用
  const guardedResult = guardrail.applyGuardrail(baseResponse.content);

  return {
    success: true,
    originalContent: guardedResult.originalResponse,
    guardedContent: guardedResult.guardedResponse,
    guardrailApplied: guardedResult.guardrailApplied,
    detectedIssues: guardedResult.issues || [],
    usage: baseResponse.usage,
  };
}
