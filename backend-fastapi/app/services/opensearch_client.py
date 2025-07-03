import os
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from typing import List, Dict, Any

class OpenSearchClient:
    def __init__(self):
        self.client = None
        self.endpoint = None
        
    async def initialize(self):
        if self.client:
            return self.client
            
        self.endpoint = os.getenv('OPENSEARCH_ENDPOINT')
        region = os.getenv('AWS_REGION', 'ap-northeast-1')
        
        if not self.endpoint:
            raise ValueError("OPENSEARCH_ENDPOINT environment variable is required")
            
        # AWS認証設定（AOSS用に修正）
        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key, 
            region,
            'aoss',  # Amazon OpenSearch Serverless用
            session_token=credentials.token
        )
        
        # ホスト名からプロトコルを除去
        host = self.endpoint.replace('https://', '').replace('http://', '')
        
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            pool_maxsize=20,
            timeout=30
        )
        
        return self.client
    
    async def test_connection(self):
        """接続テスト用メソッド"""
        try:
            client = await self.initialize()
            # AOSSではinfo()の代わりにcat.indices()を使用
            response = client.cat.indices(format='json')
            return {"status": "success", "indices": response}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
    async def search_by_text(self, index_name: str, query_text: str, size: int = 5, min_score: float = 0.001) -> List[Dict[str, Any]]:
        """改良版検索（セッションID対応）"""
        client = await self.initialize()
    
        # セッションIDパターンを検出
        import re
        is_session_id = re.match(r'^[A-Z]+-\d+\\$', query_text.strip())
    
        if is_session_id:
            # セッションID専用の検索クエリ
            search_query = {
                "size": size,
                "query": {
                    "term": {
                        "session_id": query_text
                    }
                }
            }
            print(f"🔍 Using session ID search for: {query_text}")
        else:
            # 通常の検索クエリ（session_idフィールドを追加）
            search_query = {
                "size": size,
                "min_score": min_score,
                "query": {
                    "multi_match": {
                        "query": query_text,
                        "fields": [
                            "title^3",
                            "abstract^2", 
                            "summary^2",
                            "speakers.name^2",
                            "speakers.company^2",
                            "session_id^4"  # ← セッションIDフィールドを追加（高い重み）
                        ],
                        "type": "best_fields"
                    }
                }
            }
            print(f"🔍 Using multi-field search for: {query_text}")
    
        try:
            response = client.search(index=index_name, body=search_query)
            hits = response['hits']['hits']
        
            results = []
            for hit in hits:
                results.append({
                    'id': hit['_id'],
                    'score': hit['_score'],
                    'source': hit['_source']
                })
        
            print(f"📊 Found {len(results)} results")
            for result in results:
                print(f"  - {result['source'].get('session_id')}: {result['source'].get('title')} (score: {result['score']})")
        
            return results
        
        except Exception as error:
            print(f"❌ Error in search: {error}")
            raise error

    async def search_with_transcript_content(self, index_name: str, query_text: str, size: int = 5, min_score: float = 0.001) -> List[Dict[str, Any]]:
        """非構造化データ対応のハイブリッド検索（transcript_summary含む）"""
        client = await self.initialize()
    
        # セッションIDパターンを検出
        import re
        is_session_id = re.match(r'^[A-Z]+-\d+\\$', query_text.strip())
    
        if is_session_id:
            # セッションID専用の検索クエリ
            search_query = {
                "size": size,
                "query": {
                    "term": {
                        "session_id": query_text
                    }
                }
            }
            print(f"🔍 [Transcript Search] Using session ID search for: {query_text}")
        else:
            # ハイブリッド検索クエリ（構造化データ + 非構造化データ）
            search_query = {
                "size": size,
                "min_score": min_score,
                "query": {
                    "bool": {
                        "should": [
                            # フレーズマッチング（高精度）
                            {
                                "multi_match": {
                                    "query": query_text,
                                    "fields": [
                                        "transcript_summary^4.0",  # 最高優先度
                                        "title^3.0",
                                        "abstract^2.0"
                                    ],
                                    "type": "phrase",
                                    "boost": 2.0
                                }
                            },
                            # 通常のキーワード検索
                            {
                                "multi_match": {
                                    "query": query_text,
                                    "fields": [
                                        "transcript_summary^4.0",
                                        "session_id^4.0",
                                        "title^3.0",
                                        "abstract^2.0",
                                        "summary^2.0",
                                        "speakers.name^2.0",
                                        "speakers.company^2.0"
                                    ],
                                    "type": "best_fields",
                                    "boost": 1.0
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
            print(f"🔍 [Transcript Search] Using hybrid search for: {query_text}")
    
        try:
            response = client.search(index=index_name, body=search_query)
            hits = response['hits']['hits']
        
            results = []
            for hit in hits:
                result_data = {
                    'id': hit['_id'],
                    'score': hit['_score'],
                    'source': hit['_source']
                }
                
                # transcript_summaryがマッチした場合は特別にマーク
                if 'transcript_summary' in hit['_source'] and hit['_source']['transcript_summary']:
                    result_data['has_transcript'] = True
                
                results.append(result_data)
        
            print(f"📊 [Transcript Search] Found {len(results)} results")
            for result in results:
                transcript_mark = "📄" if result.get('has_transcript') else "📋"
                print(f"  {transcript_mark} {result['source'].get('session_id')}: {result['source'].get('title')} (score: {result['score']})")
        
            return results
        
        except Exception as error:
            print(f"❌ Error in transcript search: {error}")
            raise error

# シングルトンインスタンス
opensearch_client = OpenSearchClient()
