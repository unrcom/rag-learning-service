import {
  BedrockRuntimeClient,
  InvokeModelCommand,
} from "@aws-sdk/client-bedrock-runtime";

class TitanEmbeddings {
  constructor() {
    this.client = new BedrockRuntimeClient({
      region: process.env.AWS_REGION,
      credentials: {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
      },
    });
    this.modelId = "amazon.titan-embed-text-v1";
  }

  /**
   * テキストをベクトル埋め込みに変換
   * @param {string} text - 埋め込み対象のテキスト
   * @returns {Promise<number[]>} - 1536次元のベクトル配列
   */
  async embedText(text) {
    if (!text || typeof text !== "string") {
      throw new Error("Valid text string is required for embedding");
    }

    // テキストの前処理
    const cleanText = text.trim();
    if (cleanText.length === 0) {
      throw new Error("Text cannot be empty after trimming");
    }

    // Titan Embeddings用のリクエスト
    const payload = {
      inputText: cleanText,
    };

    try {
      console.log(`🔤 Embedding text: "${cleanText.substring(0, 100)}..."`);

      const command = new InvokeModelCommand({
        modelId: this.modelId,
        contentType: "application/json",
        accept: "application/json",
        body: JSON.stringify(payload),
      });

      const response = await this.client.send(command);
      const responseBody = JSON.parse(new TextDecoder().decode(response.body));

      // ベクトル埋め込みを抽出
      const embedding = responseBody.embedding;

      if (!Array.isArray(embedding) || embedding.length !== 1536) {
        throw new Error(
          `Invalid embedding format: expected 1536-dim array, got ${
            Array.isArray(embedding) ? embedding.length : typeof embedding
          }`
        );
      }

      console.log(`✅ Embedding generated: ${embedding.length} dimensions`);
      return embedding;
    } catch (error) {
      console.error("❌ Embedding generation failed:", error);
      throw new Error(`Failed to generate embedding: ${error.message}`);
    }
  }

  /**
   * 複数テキストをバッチで埋め込み
   * @param {string[]} texts - テキスト配列
   * @returns {Promise<number[][]>} - ベクトル配列の配列
   */
  async embedTexts(texts) {
    if (!Array.isArray(texts)) {
      throw new Error("Texts must be an array");
    }

    console.log(`🔤 Batch embedding ${texts.length} texts...`);

    try {
      const embeddings = await Promise.all(
        texts.map(async (text, index) => {
          try {
            return await this.embedText(text);
          } catch (error) {
            console.error(`❌ Failed to embed text ${index}: ${error.message}`);
            throw error;
          }
        })
      );

      console.log(`✅ Batch embedding completed: ${embeddings.length} vectors`);
      return embeddings;
    } catch (error) {
      console.error("❌ Batch embedding failed:", error);
      throw error;
    }
  }

  /**
   * テキストとクエリの類似度を計算
   * @param {string} text1 - 比較元テキスト
   * @param {string} text2 - 比較先テキスト
   * @returns {Promise<number>} - コサイン類似度 (-1 ~ 1)
   */
  async calculateSimilarity(text1, text2) {
    const [embedding1, embedding2] = await Promise.all([
      this.embedText(text1),
      this.embedText(text2),
    ]);

    // コサイン類似度計算
    const dotProduct = embedding1.reduce(
      (sum, a, i) => sum + a * embedding2[i],
      0
    );
    const magnitude1 = Math.sqrt(embedding1.reduce((sum, a) => sum + a * a, 0));
    const magnitude2 = Math.sqrt(embedding2.reduce((sum, a) => sum + a * a, 0));

    const similarity = dotProduct / (magnitude1 * magnitude2);

    console.log(`📊 Similarity between texts: ${similarity.toFixed(4)}`);
    return similarity;
  }
}

export const titanEmbeddings = new TitanEmbeddings();
