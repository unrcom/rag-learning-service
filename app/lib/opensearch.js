import { Client } from "@opensearch-project/opensearch";
import { AwsSigv4Signer } from "@opensearch-project/opensearch/aws";
import { defaultProvider } from "@aws-sdk/credential-provider-node";

import { titanEmbeddings } from "./embeddings.js";

class OpenSearchClient {
  constructor() {
    this.client = null;
    this.endpoint = null;
  }

  async initialize() {
    if (this.client) return this.client;

    this.endpoint = process.env.OPENSEARCH_ENDPOINT;

    if (!this.endpoint) {
      throw new Error("OPENSEARCH_ENDPOINT environment variable is required");
    }

    console.log("Initializing OpenSearch client with endpoint:", this.endpoint);

    this.client = new Client({
      ...AwsSigv4Signer({
        region: process.env.AWS_REGION,
        service: "aoss",
        getCredentials: defaultProvider(),
      }),
      node: this.endpoint,
    });

    return this.client;
  }

  // ベクトル検索用インデックス作成（修正済み）
  async createVectorIndex(indexName = "documents") {
    const client = await this.initialize();

    const indexSettings = {
      settings: {
        "index.knn": true,
        number_of_shards: 1,
        number_of_replicas: 0,
      },
      mappings: {
        properties: {
          vector_field: {
            type: "knn_vector",
            dimension: 1536,
            method: {
              name: "hnsw",
              space_type: "l2",
              engine: "nmslib",
              parameters: {
                ef_construction: 128,
                m: 24,
              },
            },
          },
          text: {
            type: "text",
            analyzer: "standard",
          },
          title: {
            type: "text",
            analyzer: "standard",
          },
          source: {
            type: "keyword",
          },
          chunk_id: {
            type: "keyword",
          },
          metadata: {
            type: "object",
            properties: {
              created_at: { type: "date" },
              document_type: { type: "keyword" },
              page_number: { type: "integer" },
              word_count: { type: "integer" },
            },
          },
        },
      },
    };

    try {
      console.log(`Creating index: ${indexName}`);
      const response = await client.indices.create({
        index: indexName,
        body: indexSettings,
      });

      console.log("✅ Vector index created successfully");
      return response;
    } catch (error) {
      if (
        error.meta?.body?.error?.type === "resource_already_exists_exception"
      ) {
        console.log("ℹ️ Index already exists, skipping creation");
        return { acknowledged: true, existing: true };
      }

      console.error("❌ Error creating index:", error);
      throw error;
    }
  }

  // ドキュメント追加（修正版）
  async addDocument(indexName, document, documentId = null) {
    const client = await this.initialize();

    const indexParams = {
      index: indexName,
      body: document,
      // refresh: true を削除
    };

    if (documentId) {
      indexParams.id = documentId;
    }

    try {
      const response = await client.index(indexParams);
      console.log("✅ Document added:", response._id);
      return response;
    } catch (error) {
      console.error("❌ Error adding document:", error);
      throw error;
    }
  }

  // 残りのメソッドは変更なし...
  // ベクトル検索
  async vectorSearch(indexName, queryVector, size = 5, minScore = 0.001) {
    // 0.7 → 0.001 に修正
    const client = await this.initialize();

    const searchQuery = {
      size,
      min_score: minScore, // L2距離に適したスコア閾値
      query: {
        knn: {
          vector_field: {
            vector: queryVector,
            k: size,
          },
        },
      },
      _source: {
        exclude: ["vector_field"], // レスポンスサイズを削減
      },
    };

    try {
      console.log(
        `🔍 Performing vector search in index: ${indexName}, min_score: ${minScore}`
      );
      const response = await client.search({
        index: indexName,
        body: searchQuery,
      });

      const hits = response.body.hits.hits;
      console.log(
        `✅ Found ${hits.length} documents with scores: ${hits
          .map((h) => h._score.toFixed(4))
          .join(", ")}`
      );

      return hits.map((hit) => ({
        id: hit._id,
        score: hit._score,
        source: hit._source,
      }));
    } catch (error) {
      console.error("❌ Error in vector search:", error);
      throw error;
    }
  }

  async checkIndexHealth(indexName) {
    const client = await this.initialize();

    try {
      const stats = await client.indices.stats({ index: indexName });
      const settings = await client.indices.getSettings({ index: indexName });

      return {
        exists: true,
        document_count: stats.body.indices[indexName].total.docs.count,
        size_in_bytes: stats.body.indices[indexName].total.store.size_in_bytes,
        settings: settings.body[indexName].settings,
      };
    } catch (error) {
      if (error.meta?.statusCode === 404) {
        return { exists: false };
      }
      throw error;
    }
  }

  /**
   * テキストドキュメントを埋め込みベクトル付きで追加
   * @param {string} indexName - インデックス名
   * @param {Object} document - ドキュメント（textフィールド必須）
   * @returns {Promise<Object>} - 追加結果
   */
  async addTextDocument(indexName, document) {
    if (!document.text) {
      throw new Error("Document must have a text field");
    }

    try {
      console.log("🔤 Generating embedding for document...");

      // テキストをベクトル化
      const embedding = await titanEmbeddings.embedText(document.text);

      // ベクトルフィールドを追加
      const documentWithVector = {
        ...document,
        vector_field: embedding,
        metadata: {
          ...document.metadata,
          embedded_at: new Date().toISOString(),
          embedding_model: "amazon.titan-embed-text-v1",
        },
      };

      // ドキュメント追加
      const result = await this.addDocument(indexName, documentWithVector);
      console.log("✅ Text document with embedding added successfully");

      return result;
    } catch (error) {
      console.error("❌ Error adding text document:", error);
      throw error;
    }
  }

  /**
   * テキストクエリでセマンティック検索
   * @param {string} indexName - インデックス名
   * @param {string} queryText - 検索クエリ
   * @param {number} size - 取得件数
   * @param {number} minScore - 最小スコア（L2距離用に調整）
   * @returns {Promise<Array>} - 検索結果
   */
  async searchByText(indexName, queryText, size = 5, minScore = 0.001) {
    // 0.7 → 0.001 に修正
    try {
      console.log(`🔍 Semantic search for: "${queryText}"`);

      // クエリをベクトル化
      const queryVector = await titanEmbeddings.embedText(queryText);

      // ベクトル検索実行（L2距離用の設定）
      const results = await this.vectorSearch(
        indexName,
        queryVector,
        size,
        minScore
      );

      console.log(`✅ Semantic search completed: ${results.length} results`);
      return results;
    } catch (error) {
      console.error("❌ Error in semantic search:", error);
      throw error;
    }
  }

  // AWS Summit専用インデックス作成メソッドを追加
  async createAwsSummitIndex(indexName = "aws_summit_sessions") {
    const client = await this.initialize();

    const indexSettings = {
      settings: {
        "index.knn": true,
        number_of_shards: 1,
        number_of_replicas: 0,
      },
      mappings: {
        properties: {
          // ベクトル検索用（既存維持）
          vector_field: {
            type: "knn_vector",
            dimension: 1536,
            method: {
              name: "hnsw",
              space_type: "l2",
              engine: "nmslib",
              parameters: {
                ef_construction: 128,
                m: 24,
              },
            },
          },

          // 基本セッション情報
          title: { type: "text", analyzer: "standard" },
          session_id: { type: "keyword" },
          abstract: { type: "text", analyzer: "standard" },

          // 講演者情報（配列対応）
          speakers: {
            type: "nested",
            properties: {
              name: { type: "text", analyzer: "standard" },
              title: { type: "text", analyzer: "standard" },
              company: { type: "text", analyzer: "standard" },
            },
          },

          // セッション分類
          track: { type: "keyword" }, // KEY, AI, Cloud Infrastructure等
          level: { type: "keyword" }, // 000, 200, 300等
          session_type: { type: "keyword" },

          // 開催情報
          date: { type: "date", format: "yyyy-MM-dd" },
          start_time: { type: "keyword" },
          end_time: { type: "keyword" },
          duration: { type: "integer" },
          room: { type: "keyword" },

          // Phase 2用（未来対応）
          has_transcript: { type: "boolean" },
          transcript: { type: "text", analyzer: "standard" },
          summary: { type: "text", analyzer: "standard" },

          // メタデータ
          metadata: {
            type: "object",
            properties: {
              created_at: { type: "date" },
              source: { type: "keyword" },
              data_version: { type: "keyword" },
            },
          },
        },
      },
    };

    try {
      console.log(`Creating AWS Summit index: ${indexName}`);
      const response = await client.indices.create({
        index: indexName,
        body: indexSettings,
      });

      console.log("✅ AWS Summit index created successfully");
      return response;
    } catch (error) {
      if (
        error.meta?.body?.error?.type === "resource_already_exists_exception"
      ) {
        console.log("ℹ️ AWS Summit index already exists, skipping creation");
        return { acknowledged: true, existing: true };
      }

      console.error("❌ Error creating AWS Summit index:", error);
      throw error;
    }
  }

  /**
   * AWS Summitセッションを埋め込みベクトル付きで追加
   * @param {Object} sessionData - セッションデータ
   * @returns {Promise<Object>} - 追加結果
   */
  async addAwsSummitSession(sessionData, indexName = "aws_summit_sessions") {
    // 講演者情報を配列から抽出して検索対象テキストに含める
    const speakersText = sessionData.speakers
      .map((speaker) => `${speaker.name} ${speaker.title} ${speaker.company}`)
      .join(" ");

    // 検索対象テキストを構築（タイトル + 概要 + 講演者情報 + トラック）
    const searchableText = [
      sessionData.title,
      sessionData.abstract,
      speakersText,
      sessionData.track,
    ]
      .filter(Boolean)
      .join(" ");

    try {
      console.log(
        `🔤 Adding AWS Summit session: ${sessionData.session_id} - ${sessionData.title}`
      );

      // テキストをベクトル化
      const embedding = await titanEmbeddings.embedText(searchableText);

      // セッションデータにベクトルを追加
      const sessionWithVector = {
        ...sessionData,
        vector_field: embedding,
        metadata: {
          ...sessionData.metadata,
          created_at: new Date().toISOString(),
          source: "aws_summit_2025",
          data_version: "1.0",
        },
      };

      // セッション追加（Document IDを指定しない！）
      const result = await this.addDocument(indexName, sessionWithVector); // 第3引数を削除
      console.log(`✅ AWS Summit session added: ${sessionData.session_id}`);

      return result;
    } catch (error) {
      console.error(`❌ Error adding AWS Summit session:`, error);
      throw error;
    }
  }
}

export const opensearchClient = new OpenSearchClient();
