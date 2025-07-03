// コスト認識ガードレール
export class CostAwarenessGuardrail {
  constructor() {
    this.costMinimizers = [
      "安い",
      "安価",
      "格安",
      "数百円",
      "数千円のみ",
      "ほぼ無料",
      "低コスト",
      "お手頃",
      "わずか",
      "少額",
      "気にせず",
      "心配ありません",
      "経済的",
      "非常に低い",
      "5ドル",
      "数ドル",
      "10ドル以下",
      "無料同然",
    ];
  }

  // コスト過小評価検出
  detectCostMinimization(response) {
    const text = response.toLowerCase();
    const detectedIssues = this.costMinimizers.filter((phrase) =>
      text.includes(phrase.toLowerCase())
    );

    return {
      detected: detectedIssues.length > 0,
      issues: detectedIssues,
      severity: detectedIssues.length >= 2 ? "high" : "medium",
    };
  }

  // ガードレール適用
  applyGuardrail(response) {
    const detection = this.detectCostMinimization(response);

    if (!detection.detected) {
      return {
        originalResponse: response,
        guardedResponse: response,
        guardrailApplied: false,
      };
    }

    const warning = `

💰 重要なコスト留意点:
• RAGシステムのコストは使用量に大きく依存します
• OpenSearch Serverless: 最小構成でも月額\$80-100程度
• 本格運用前には詳細なコスト試算が必須です
• AWS Cost Budgetsでの監視設定を推奨します

⚠️ この回答は学習支援目的です。正確なコスト計画は最新料金表をご確認ください。

🚨 検出された過小評価表現: ${detection.issues.join(", ")}
`;

    return {
      originalResponse: response,
      guardedResponse: response + warning,
      guardrailApplied: true,
      issues: detection.issues,
      severity: detection.severity,
    };
  }
}

// テスト用関数
export function testGuardrail() {
  const guardrail = new CostAwarenessGuardrail();

  // Claude 2.1の中国語回答（翻訳版）をテスト
  const testResponse =
    "RAGシステムは非常に経済的な選択です。月5ドル程度で運用でき、個人開発者にとってはお手頃な価格です。";

  const result = guardrail.applyGuardrail(testResponse);

  console.log("=== ガードレールテスト ===");
  console.log("元の回答:", result.originalResponse);
  console.log("ガードレール発動:", result.guardrailApplied);
  console.log("検出された問題:", result.issues);

  return result;
}
