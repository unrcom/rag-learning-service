# app/api/debug.py を修正
from fastapi import APIRouter, HTTPException
from app.services.opensearch_client import opensearch_client
from typing import List, Dict, Any
import os

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/connection-test")
async def test_connection():
    """OpenSearch Serverless接続テスト"""
    try:
        result = await opensearch_client.test_connection()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")

@router.get("/indices")
async def list_indices():
    """利用可能なインデックス一覧（AOSS対応）"""
    try:
        client = await opensearch_client.initialize()
        
        # AOSSでインデックス一覧を取得
        response = client.cat.indices(format='json')
        
        indices = []
        for index_info in response:
            indices.append({
                "name": index_info.get('index', 'unknown'),
                "status": index_info.get('status', 'unknown'),
                "document_count": index_info.get('docs.count', 'unknown'),
                "size": index_info.get('store.size', 'unknown')
            })
        
        return {
            "total_indices": len(indices),
            "indices": indices
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing indices: {str(e)}")

@router.get("/sessions")
async def get_all_sessions():
    """全セッション取得（動的インデックス検索）"""
    try:
        # まずインデックス一覧を取得
        client = await opensearch_client.initialize()
        indices_response = client.cat.indices(format='json')
        
        available_indices = [idx['index'] for idx in indices_response]
        configured_index = os.getenv('OPENSEARCH_INDEX', 'aws-summit-sessions')
        
        # 使用するインデックスを決定
        if configured_index in available_indices:
            index_name = configured_index
        else:
            # summit, session, ragなどのキーワードで検索
            possible_indices = [
                idx for idx in available_indices 
                if any(keyword in idx.lower() for keyword in ['summit', 'session', 'rag', 'aws'])
            ]
            if possible_indices:
                index_name = possible_indices[0]
            else:
                return {
                    "error": "No suitable index found",
                    "configured_index": configured_index,
                    "available_indices": available_indices,
                    "suggestion": "Please check your index name or create the index first"
                }
        
        # ドキュメント取得
        body = {
            "query": {"match_all": {}},
            "size": 50
        }
        
        response = client.search(index=index_name, body=body)
        
        sessions = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            sessions.append({
                "session_id": source.get('session_id'),
                "title": source.get('title'),
                "speakers": source.get('speakers', []),
                "summary": source.get('summary', ''),
                "abstract": source.get('abstract', ''),
                "document_id": hit['_id']
            })
        
        return {
            "used_index": index_name,
            "configured_index": configured_index,
            "available_indices": available_indices,
            "total_sessions": len(sessions),
            "sessions": sessions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sessions: {str(e)}")

@router.get("/check-environment")
async def check_environment():
    """環境変数確認（簡易版）"""
    env_vars = {
        "OPENSEARCH_ENDPOINT": os.getenv('OPENSEARCH_ENDPOINT'),
        "OPENSEARCH_INDEX": os.getenv('OPENSEARCH_INDEX', 'aws-summit-sessions'),
        "AWS_REGION": os.getenv('AWS_REGION', 'ap-northeast-1')
    }
    
    return {
        "environment_variables": env_vars,
        "endpoint_format": "Serverless format detected" if '.aoss.amazonaws.com' in env_vars["OPENSEARCH_ENDPOINT"] else "Regular OpenSearch format"
    }

@router.get("/test-sony-search")
async def test_sony_search():
    """ソニー関連の様々な検索パターンをテスト"""
    test_queries = [
        "ソニーグループ",
        "ソニー", 
        "大場正博",
        "平野太一",
        "Agentic AI",
        "CUS-03"
    ]
    
    # 正しいインデックス名を使用
    index_name = "aws_summit_sessions"
    
    results = {}
    for query in test_queries:
        try:
            search_results = await opensearch_client.search_by_text(
                index_name,
                query,
                size=5
            )
            results[query] = {
                "count": len(search_results),
                "sessions": [
                    {
                        "session_id": result['source'].get('session_id'),
                        "title": result['source'].get('title'),
                        "score": result['score']
                    }
                    for result in search_results
                ]
            }
        except Exception as e:
            results[query] = {"error": str(e)}
    
    return results


@router.get("/search-details")
async def search_with_details(query: str):
    """検索結果の詳細情報を返す"""
    try:
        index_name = "aws_summit_sessions"  # 正しいインデックス名を直接指定
        client = await opensearch_client.initialize()
        
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title", "abstract", "summary", "speakers.name", "speakers.company"],
                    "type": "best_fields"
                }
            },
            "size": 10,
            "explain": True
        }
        
        response = client.search(index=index_name, body=search_body)
        
        results = []
        for hit in response['hits']['hits']:
            results.append({
                "session_id": hit['_source'].get('session_id'),
                "title": hit['_source'].get('title'),
                "score": hit['_score'],
                "speakers": hit['_source'].get('speakers', []),
                "summary_preview": hit['_source'].get('summary', '')[:200] + "..." if len(hit['_source'].get('summary', '')) > 200 else hit['_source'].get('summary', ''),
                "abstract_preview": hit['_source'].get('abstract', '')[:200] + "..." if len(hit['_source'].get('abstract', '')) > 200 else hit['_source'].get('abstract', ''),
            })
        
        return {
            "query": query,
            "index_used": index_name,
            "total_hits": response['hits']['total']['value'],
            "max_score": response['hits']['max_score'],
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in detailed search: {str(e)}")

    @router.get("/index-mapping")
    async def get_index_mapping():
        """インデックスのマッピング構造を確認"""
        try:
            client = await opensearch_client.initialize()
            mapping = client.indices.get_mapping(index="aws_summit_sessions")
            return mapping
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting mapping: {str(e)}")

@router.get("/index-mapping")
async def get_index_mapping():
    """インデックスのマッピング構造を確認"""
    try:
        client = await opensearch_client.initialize()
        mapping = client.indices.get_mapping(index="aws_summit_sessions")
        return mapping
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting mapping: {str(e)}")

@router.get("/session-field-test/{session_id}")
async def test_session_field(session_id: str):
    """セッションIDフィールドの検索テスト"""
    try:
        client = await opensearch_client.initialize()
        
        # 複数の検索パターンをテスト
        test_queries = [
            {"term": {"session_id": session_id}},
            {"term": {"session_id.keyword": session_id}},
            {"match": {"session_id": session_id}},
            {"wildcard": {"session_id": f"*{session_id}*"}}
        ]
        
        results = {}
        for i, query in enumerate(test_queries):
            try:
                response = client.search(
                    index="aws_summit_sessions",
                    body={"query": query, "size": 5}
                )
                results[f"pattern_{i+1}"] = {
                    "query": query,
                    "hits": len(response['hits']['hits']),
                    "titles": [hit['_source'].get('title') for hit in response['hits']['hits']]
                }
            except Exception as e:
                results[f"pattern_{i+1}"] = {"error": str(e)}
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing session field: {str(e)}")
