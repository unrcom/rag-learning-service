# AWS Summit Japan 2025 講演検索 RAG システム

段階的 RAG システム構築プロジェクト - JavaScript から Python への技術移行とスキルアップを目的とした実践的学習プロジェクト

## 🏗️ システム構成

### Phase 1: Naive RAG ✅ 完了

- **技術**: Next.js + JavaScript
- **場所**: `app/`
- **状態**: 完成・動作確認済み
- **特徴**: 基本的な RAG 実装、AWS Summit データ対応

### Phase 2: Advanced RAG ✅ 完了

- **技術**: FastAPI + Python + OpenSearch + Bedrock
- **場所**: `backend-fastapi/`
- **主要機能**:
  - LLM 形態素解析によるキーワード抽出
  - スコアベース優先度検索システム
  - 非構造化データ統合（transcript_summary）
  - Claude 3 Haiku 高速化（19 秒 →7 秒）
  - ハイブリッド検索（構造化+非構造化データ）

### Phase 3: Modular RAG 🚧 計画中

- **技術**: 複数 RAG モジュール + AWS Bedrock Agent
- **場所**: `backend-modular-rag/`（予定）
- **計画**: 複合クエリ対応、結果統合システム

## 🚀 セットアップ手順

### 1. 環境変数設定

```bash
cp .env.example .env
# .envファイルを編集してAWS認証情報を設定
2. Phase 1 (Next.js Naive RAG) 起動
npm install
npm run dev
# http://localhost:3000 でアクセス
3. Phase 2 (Advanced RAG) 起動
cd backend-fastapi
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
4. Phase 2 テスト実行
curl -X POST "http://localhost:8000/api/v2/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "RAGの3つの発展段階について教えてください"}'
📊 パフォーマンス実績
Phase 2 Advanced RAG
OpenSearch検索: ~0.1秒
LLM処理: ~7秒（Claude 3 Haiku）
全体処理: ~9秒
改善効果: Claude v2:1比で55%高速化（20秒→9秒）
🗂️ データ構成
構造化データ: AWS Summit 2025の10セッション情報
非構造化データ: 詳細講演要約（RAG技術解説等）
検索対象フィールド: title, abstract, speakers, transcript_summary
検索エンジン: Amazon OpenSearch Serverless
🔧 技術スタック
Phase 1 (Naive RAG)
Next.js 15
JavaScript
AWS SDK
Phase 2 (Advanced RAG)
FastAPI (Python)
Amazon OpenSearch Serverless
Amazon Bedrock (Claude 3 Haiku)
LLM形態素解析
ハイブリッド検索
🎯 学習目標の達成状況
✅ JavaScript → Python移行体験
✅ 基本RAG → Advanced RAGの段階的理解
✅ AWS服務活用（OpenSearch、Bedrock）
✅ 実用的性能（9秒高速応答）
✅ 非構造化データ活用
🚧 Modular RAG設計（Phase 3）
🔒 セキュリティ
環境変数による認証情報管理
AWS IAM権限制御
.gitignoreによる機密情報保護
CORS設定によるアクセス制御
📝 ライセンス
このプロジェクトは学習目的で作成されました。

🚀 次のステップ
Phase 3: Modular RAGシステムの実装予定

複数RAGモジュールの並列実行
結果統合システム
AWS Bedrock Agent統合
```
