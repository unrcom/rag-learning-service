import os
import sys
import asyncio
import json
import time

# プロジェクトのルートパスを追加（インポートエラー回避）
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.opensearch_client import opensearch_client
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# 講演要約データ（既存と同じ）
transcript_data = {
    "AWS-08": """# 生成AIのためのデータ活用実践ガイド要約

## 講演者・セッション概要
- **講演者**: AWS Japan ソリューションアーキテクト タカノ氏
- **専門領域**: 製造業顧客支援、Amazon Timestreamを含むデータベース系サービス
- **レベル**: 300（技術メイン、ファインチューニング・モデル学習は対象外）
- **目標**: RAG実装の考え方・設計・実装ヒントの提供

## 具体的ユースケース：自動車保険検討システム

### シナリオ設定
- **ユーザー**: Pat（新車購入、旧車売却済み）
- **ニーズ**: 新車用自動車保険の料金・補償内容比較検討
- **提供サービス**: 生成AIを使ったバーチャルアシスタント（チャットアプリ）

### RAGが必要な理由
- **問題**: 単純な質問では一般的な回答しか得られない
- **解決**: パーソナライズされた回答にはユーザー情報と保険会社情報が必要
- **効果**: 詳細な見積もり提供が可能

## RAGにおける2つのコンテキスト

### 1. 状況コンテキスト
- **定義**: ユーザーの人物・現在状況・事実についての情報
- **例**: Patの運転履歴、車のスペック
- **保存場所**: 既存データベース（構造化されて整理済み）

### 2. セマンティックコンテキスト
- **定義**: 質問・事実に関連する類似情報、意味を与える情報
- **例**: 法律・規則・ルール、保険料情報
- **保存場所**: ベクトルデータベース（意味的類似性に基づく検索のため）

## 拡張プロンプトの4つの構成要素

1. **基盤モデルの指示**（システムプロンプト）
2. **状況コンテキスト**（データベースから取得した事実情報）
3. **セマンティックコンテキスト**（ベクトル検索で取得した関連情報）
4. **ユーザーの質問**

## RAGの3つの発展段階

### 1. Naive RAG（基本）
- **特徴**: 全てのRAGの基本、シンプル
- **適用場面**: 誰にでも同じような回答で十分な場合
- **課題**: データのニュアンスを捉えられない（例：保険料200～5,000ドルという幅広い回答）

### 2. Advanced RAG
- **目的**: より最適な回答のための複数検索手法組み合わせ
- **3つのアプローチ**:
  1. **検索前処理**: 質問のカスタマイズ、リライティング、ガードレール
  2. **コンテキスト検索**: 高度な検索手法
  3. **検索後処理**: フィルタリング、リランキング、要約

#### Advanced RAGの検索手法

##### ハイブリッド検索
- **組み合わせ**: ベクトル検索 + 全文検索 + リランキング
- **メリット**: 
  - ベクトル検索: 固有名詞・専門用語の取りこぼし補完
  - キーワード検索: 表現の違い・言い換えへの対応
- **用途**: コンテンツ生成など、正確な事実情報と意味的近似情報の組み合わせ

##### グラフRAG
- **特徴**: 複雑な情報の関連性が必要な場合に効果を発揮
- **AWS対応**: Amazon Neptune Analytics

##### 自然言語→SQL変換
- **用途**: 明確にSQL化できる質問
- **メリット**: 全データのベクトル化が不要、既存データベース活用

### 3. Modular RAG
- **目的**: 複数のナレッジベース・処理の最適な組み合わせとタイミングの自動化
- **実装**: AWS Bedrock Agentを活用したオーケストレーション
- **効果**: ユーザー入力から対応内容を自動判断し、順番・やり取りを最適化

## データ基盤構築

### データソースの分類
1. **構造化データ**: データベース内の定義されたスキーマデータ
2. **半構造化データ**: JSON、XML（時間とともにスキーマが変化）
3. **非構造化データ**: 文書ファイル・画像（埋め込みモデルでベクトル化が必要）

### チャンキング手法

#### 1. 固定長チャンキング
- **メリット**: 実装が簡単
- **デメリット**: 意味の区切りを無視、コンテキストを失う可能性

#### 2. スキーマ定義
- **メリット**: コンテキストをしっかり捉える
- **デメリット**: 全て手動定義が必要で大変

#### 3. 階層チャンキング（Hierarchical Chunking）
- **特徴**: グループ・階層ごとに分割
- **AWS実装**: Bedrock Knowledge Baseの親チャンク・子チャンク機能
- **デメリット**: ドメイン知識が必要

#### 4. セマンティックチャンキング
- **特徴**: LLMを使用した意味を考慮した分割
- **メリット**: 最も良いコンテキスト取得の可能性
- **デメリット**: 時間・リソースコストが高い

### チャンクサイズの選択
- **小さなチャンク**: シンプルな質問対応、ポイント取得に適している
- **大きなチャンク**: 深い文書解釈・要約が必要な場合、全体文脈把握が重要

### ベクトルデータベース選択基準
- **最優先**: 馴染みがあり使いやすいもの
- **理由**: 実装の慣れが最も重要
- **AWS提供**: 各種ベクトル検索対応データベース

## データ管理・ガバナンス

### データ分散による課題
- **データサイロ化**: 各所に散在するデータ
- **データリネージ**: データの出所追跡
- **データ品質**: 正確性の担保
- **アクセスコントロール**: 適切な権限管理

### データ基盤アーキテクチャのベストプラクティス

#### 1. 疎結合設計
- データ保存と処理を分離
- 部分変更・再利用の容易さ

#### 2. 適切なツール選択
- リアルタイム→ストリーミング処理サービス
- バッチ→データウェアハウス

#### 3. マネージドサービス活用
- クラスター管理・運用をAWSに委任
- アプリケーション開発・UX向上に集中

#### 4. ログ中心データデザイン
- 全データをイミュータブルなログとしてデータレイクに保存
- バグ・不具合時の復旧可能性確保

#### 5. コスト意識
- 設計段階でのコスト見積もり
- 無駄の確認と最適化

## 推奨アーキテクチャ構成

### フロントエンド（ユーザーアクセス）
- **レスポンス要件**: ミリ秒→RDBMS/ベクトルDB、秒→データレイク
- **構成要素**:
  - 会話状態管理（DynamoDB）
  - 状況コンテキスト（既存DB）
  - セマンティックコンテキスト（ベクトルDB）

### バックエンド（データ収集・管理）
- **データレイク**: S3中心の構成
- **オープンテーブルフォーマット**: 更新しやすいParquet形式
- **メタデータ管理**: AWS Glue Data Catalog

### データガバナンス
- **カタログ化**: AWS LakeFormation
- **アクセス制御**: 管理側許可によるデータ利用
- **データ品質**: AWS Glue Data Quality（SQL宣言的ルール）
- **リネージ管理**: LakeFormationによるデータ系譜追跡

## まとめ・推奨アプローチ

### 段階的発展
1. **Naive RAGから開始**: 基本構成で開始
2. **段階的発展**: 要件に応じてAdvanced/Modular RAGへ

### データ活用の考え方
- **全ベクトル化は不要**: 既存データの活用
- **最適なアーキテクチャ**: コンテキスト提供のための設計
- **自動化推進**: RAGパイプラインの可能な限りの自動化

### 価値提供への集中
- ユーザー価値に直結しない部分の自動化
- より良いユーザー体験実現への注力"""
}

async def find_session_by_id(session_id: str):
    """セッションIDでドキュメントを検索"""
    try:
        client = await opensearch_client.initialize()
        
        search_query = {
            "query": {
                "term": {
                    "session_id": session_id
                }
            }
        }
        
        response = client.search(index="aws_summit_sessions", body=search_query)
        
        if response['hits']['hits']:
            return response['hits']['hits'][0]
        return None
        
    except Exception as e:
        print(f"❌ Error finding session {session_id}: {e}")
        return None

async def create_enhanced_session_document(session_id: str, transcript_content: str):
    """新しい拡張セッションドキュメントを作成"""
    try:
        print(f"🔍 Searching for original session: {session_id}")
        
        # 元のセッションを検索
        hit = await find_session_by_id(session_id)
        
        if hit:
            original_doc = hit['_source']
            print(f"✅ Found original session: {original_doc['title']}")
            
            # 拡張ドキュメントを作成
            enhanced_doc = original_doc.copy()
            enhanced_doc['transcript_summary'] = transcript_content
            enhanced_doc['has_detailed_content'] = True
            enhanced_doc['data_version'] = 'enhanced_v1'
            enhanced_doc['enhanced_timestamp'] = time.time()
            
            # 新しいドキュメントとして追加
            client = await opensearch_client.initialize()
            response = client.index(
                index="aws_summit_sessions",
                body=enhanced_doc
            )
            
            new_doc_id = response['_id']
            print(f"✅ Successfully created enhanced session document")
            print(f"📄 New document ID: {new_doc_id}")
            print(f"📄 Added transcript summary ({len(transcript_content)} characters)")
            print(f"🔗 Original document preserved")
            
            return True
            
        else:
            print(f"❌ Original session {session_id} not found")
            return False
            
    except Exception as e:
        print(f"❌ Error creating enhanced session {session_id}: {e}")
        print(f"🔍 Error details: {type(e).__name__}: {str(e)}")
        return False

async def verify_enhanced_session(session_id: str):
    """拡張セッションの作成を確認"""
    try:
        client = await opensearch_client.initialize()
        
        # 拡張セッションを検索
        search_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"session_id": session_id}},
                        {"term": {"has_detailed_content": True}}
                    ]
                }
            }
        }
        
        response = client.search(index="aws_summit_sessions", body=search_query)
        
        if response['hits']['hits']:
            enhanced_doc = response['hits']['hits'][0]['_source']
            summary_length = len(enhanced_doc.get('transcript_summary', ''))
            has_detailed = enhanced_doc.get('has_detailed_content', False)
            
            print(f"✅ Enhanced session verification successful for {session_id}")
            print(f"   - transcript_summary: {summary_length} characters")
            print(f"   - has_detailed_content: {has_detailed}")
            print(f"   - data_version: {enhanced_doc.get('data_version', 'unknown')}")
            return True
        else:
            print(f"❌ Enhanced session verification failed for {session_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying enhanced session {session_id}: {e}")
        return False

async def main():
    """メイン実行関数（修正版）"""
    print("🚀 Starting transcript data integration (Enhanced Version)...")
    print("=" * 60)
    
    success_count = 0
    total_count = len(transcript_data)
    
    # 各セッションの要約データを投入
    for session_id, transcript_content in transcript_data.items():
        print(f"\n📋 Processing session: {session_id}")
        print("-" * 40)
        
        # 拡張ドキュメント作成
        if await create_enhanced_session_document(session_id, transcript_content):
            # 作成確認
            if await verify_enhanced_session(session_id):
                success_count += 1
                print(f"🎉 Session {session_id} enhancement completed!")
            else:
                print(f"⚠️ Session {session_id} enhancement verification failed")
        else:
            print(f"💥 Session {session_id} enhancement failed")
    
    print("\n" + "=" * 60)
    print(f"📊 Enhancement Summary:")
    print(f"   - Total sessions: {total_count}")
    print(f"   - Successful: {success_count}")
    print(f"   - Failed: {total_count - success_count}")
    
    if success_count == total_count:
        print("🎉 All transcript data successfully integrated!")
        print("📋 Note: Original sessions preserved, enhanced versions created")
    else:
        print("⚠️ Some enhancements failed. Please check the logs above.")

if __name__ == "__main__":
    asyncio.run(main())
