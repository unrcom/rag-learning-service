from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse, Source
from app.services.opensearch_client import opensearch_client
from app.services.bedrock_client import bedrock_client
from typing import List, Tuple
import os
import re
import time
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

router = APIRouter()

def calculate_priority_score(keyword: str, category: str) -> int:
    """改良版：完全な企業名を最優先にする優先度スコア計算"""
    score = 0
    
    # 完全な企業名・組織名が最高優先度
    if '企業名' in category and 'の一部' not in category:
        score += 1000
    elif '組織名' in category and 'の一部' not in category:
        score += 950
    # 企業名・組織名の一部は中程度優先度
    elif '企業名の一部' in category:
        score += 700
    elif '組織名の一部' in category:
        score += 650
    # その他の固有名詞
    elif '固有名詞' in category:
        score += 800
    
    # サービス名、製品名、ゲーム名（完全形を優先）
    if any(x in category for x in ['サービス名', 'サービス']) and 'の一部' not in category:
        score += 900
    elif any(x in category for x in ['製品名', '製品']) and 'の一部' not in category:
        score += 900
    elif any(x in category for x in ['ゲーム名', 'ゲーム']) and 'の一部' not in category:
        score += 900
    # 部分的なサービス名・製品名
    elif any(x in category for x in ['サービス', '製品', 'ゲーム']) and 'の一部' in category:
        score += 600
    
    # 技術用語
    if '技術' in category:
        score += 500
    
    # 専門用語
    if '専門' in category:
        score += 400
    
    # 一般名詞は低優先度
    if category == '名詞':
        score += 200
    
    # 数詞は中程度
    if '数詞' in category:
        score += 300
    
    # 文字数による微調整（長いほど具体的）
    score += len(keyword) * 5
    
    # 特定の重要キーワードにボーナス（完全一致のみ）
    important_terms = [
        'ソニーグループ', 'カプコン', 'リコー', 'atama plus',
        'Amazon', 'AWS', 'Bedrock', 'Claude',
        'モンスターハンターワイルズ', 'モンスターハンター',
        'Agentic AI', '生成AI'
    ]
    
    if keyword in important_terms:
        score += 100
    
    return score

async def search_with_score_based_fallback(query: str, keywords_with_scores: list) -> Tuple[list, str, float]:
    """スコアベースのフォールバック検索システム（実行時間測定付き）"""
    opensearch_start = time.time()
    
    if not keywords_with_scores:
        print("⚠️ No keywords available, using original query")
        results = await opensearch_client.search_with_transcript_content("aws_summit_sessions", query, 3)
        opensearch_time = time.time() - opensearch_start
        return results, query, opensearch_time
    
    # 試行するキーワードを準備
    search_candidates = []
    
    # 主要キーワード（スコア順）
    for keyword_info in keywords_with_scores:
        keyword = keyword_info['keyword']
        score = keyword_info['priority']
        
        search_candidates.append({
            'keyword': keyword,
            'score': score,
            'reason': 'primary' if score < 1000 else 'high_specificity'
        })
    
    # 高スコア（≥1000）の場合、より一般的なキーワードをフォールバック候補に追加
    high_score_keywords = [k for k in keywords_with_scores if k['priority'] >= 1000]
    if high_score_keywords:
        print(f"🔄 High specificity keywords detected: {[k['keyword'] for k in high_score_keywords]}")
        
        # より一般的なキーワードを探してフォールバック候補に追加
        for keyword_info in keywords_with_scores:
            if 500 <= keyword_info['priority'] < 1000:
                search_candidates.append({
                    'keyword': keyword_info['keyword'],
                    'score': keyword_info['priority'],
                    'reason': 'fallback_general'
                })
    
    # 重複除去（キーワード順序を保持）
    seen_keywords = set()
    unique_candidates = []
    for candidate in search_candidates:
        if candidate['keyword'] not in seen_keywords:
            unique_candidates.append(candidate)
            seen_keywords.add(candidate['keyword'])
    
    print(f"🎯 Search strategy: {len(unique_candidates)} candidates")
    for i, candidate in enumerate(unique_candidates):
        print(f"   {i+1}. '{candidate['keyword']}' (score: {candidate['score']}, reason: {candidate['reason']})")
    
    # 順次検索実行（非構造化データ対応）
    for i, candidate in enumerate(unique_candidates):
        keyword = candidate['keyword']
        reason = candidate['reason']
        
        print(f"🔍 Search attempt {i+1}: '{keyword}' (score: {candidate['score']}, reason: {reason})")
        
        results = await opensearch_client.search_with_transcript_content("aws_summit_sessions", keyword, 3)
        
        if results and len(results) > 0:
            opensearch_time = time.time() - opensearch_start
            print(f"✅ Success with '{keyword}' - Found {len(results)} results (OpenSearch time: {opensearch_time:.3f}s)")
            return results, keyword, opensearch_time
        else:
            print(f"❌ No results with '{keyword}'")
    
    # 最終フォールバック: 元のクエリ（非構造化データ対応）
    print(f"🆘 Final fallback with original query: '{query}'")
    final_results = await opensearch_client.search_with_transcript_content("aws_summit_sessions", query, 3)
    opensearch_time = time.time() - opensearch_start
    return final_results, query, opensearch_time

def parse_and_prioritize_keywords_advanced(llm_result: str) -> list:
    """キーワード情報を詳細に保持する版"""
    keywords = []
    lines = llm_result.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or any(skip in line for skip in ['解析結果', '質問の', '以下の']):
            continue
            
        import re
        pattern = r'^([^(（]+)[（(]([^)）]+)[）)]'
        match = re.match(pattern, line)
        
        if match:
            keyword = match.group(1).strip()
            category = match.group(2).strip()
            
            if len(keyword) > 1 and keyword not in ['について', 'を', 'の', 'が', 'は']:
                priority_score = calculate_priority_score(keyword, category)
                keywords.append({
                    'keyword': keyword,
                    'category': category,
                    'priority': priority_score,
                    'length': len(keyword)
                })
                print(f"✅ Keyword: '{keyword}', Category: '{category}', Priority: {priority_score}")
    
    if not keywords:
        print("⚠️ No keywords extracted from advanced parsing")
        return []
    
    # 優先度スコア順でソート（高い順）
    keywords.sort(key=lambda x: (x['priority'], x['length']), reverse=True)
    
    print(f"🔄 Advanced prioritized keywords:")
    for i, k in enumerate(keywords):
        fallback_indicator = " (FALLBACK CANDIDATE)" if k['priority'] >= 1000 else ""
        print(f"   {i+1}. '{k['keyword']}' (priority: {k['priority']}, category: {k['category']}){fallback_indicator}")
    
    return keywords

async def extract_search_keywords_with_llm(query: str) -> Tuple[str, float]:
    """スコアベースフォールバック対応版（LLM実行時間測定付き）"""
    
    # セッションIDは従来通り
    session_id_match = re.search(r'[A-Z]+-\d+', query)
    if session_id_match:
        return session_id_match.group(), 0.0
    
    llm_keyword_start = time.time()
    
    extraction_prompt = f"""以下のユーザーの質問を形態素解析して、検索に有用なキーワードを抽出してください。

質問: {query}

ルール:
- 企業名、組織名、サービス名、製品名などの固有名詞は、完全形と構成要素の両方を出力する
- 各キーワードに品詞と詳細な分類を付与する
- 助詞、動詞、形容詞は除外する
- 以下の形式で厳密に出力する：

キーワード(品詞・分類)

例:
入力: "ソニーグループの取り組みについて教えてください"
出力: 
ソニー(固有名詞・企業名の一部)
ソニーグループ(固有名詞・企業名)
グループ(名詞)
取り組み(名詞)

解析結果:"""

    try:
        llm_result = await bedrock_client.generate_guarded_response(extraction_prompt)
        llm_keyword_time = time.time() - llm_keyword_start
        print(f"🧠 LLM keyword extraction completed in {llm_keyword_time:.3f}s")
        print(f"🧠 LLM analysis result:\n{llm_result}")
        
        # 詳細なキーワード情報を取得
        keywords_with_scores = parse_and_prioritize_keywords_advanced(llm_result)
        
        if keywords_with_scores:
            # スコアベースフォールバック検索を実行（時間測定は内部で実行済み）
            search_results, selected_keyword, opensearch_time = await search_with_score_based_fallback(
                query, keywords_with_scores
            )
            
            total_llm_time = llm_keyword_time  # キーワード抽出時間のみ
            print(f"🎯 Selected keyword after fallback: '{selected_keyword}' (LLM keyword time: {total_llm_time:.3f}s)")
            return selected_keyword, total_llm_time
        
        print("⚠️ No keywords extracted, using original query")
        return query, llm_keyword_time
        
    except Exception as e:
        llm_keyword_time = time.time() - llm_keyword_start
        print(f"❌ LLM extraction failed: {e} (time: {llm_keyword_time:.3f}s)")
        return query, llm_keyword_time

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    # 全体処理時間の測定開始
    total_start = time.time()
    
    try:
        message = request.message.strip()
        
        if not message:
            raise HTTPException(status_code=400, detail="メッセージが空です")
        
        print(f"💬 User query: \"{message}\"")
        
        # LLMを使った高度な構造化キーワード抽出（実行時間測定付き）
        search_query, llm_keyword_time = await extract_search_keywords_with_llm(message)
        print(f"🔍 Final search query: \"{search_query}\"")
        
        # OpenSearch検索の実行時間測定
        opensearch_start = time.time()
        search_results = await opensearch_client.search_with_transcript_content(
            "aws_summit_sessions",
            search_query,
            3
        )
        opensearch_time = time.time() - opensearch_start
        
        print(f"📊 Found {len(search_results)} relevant documents (OpenSearch time: {opensearch_time:.3f}s)")
        
        # transcript_summaryが含まれる結果の確認
        transcript_count = sum(1 for result in search_results if result.get('has_transcript'))
        if transcript_count > 0:
            print(f"📄 Including {transcript_count} results with detailed transcript content")
        
        # 2. コンテキストを構築
        context = ""
        sources = []
        
        if search_results:
            context = "以下の情報を参考にして回答してください：\n\n"
            
            for index, result in enumerate(search_results):
                context += f"【参考資料{index + 1}】\n"
                context += f"タイトル: {result['source']['title']}\n"
                
                # AWS Summit用データ構造に対応
                if 'abstract' in result['source']:
                    context += f"概要: {result['source']['abstract']}\n"
                
                # 詳細な講演要約がある場合は優先的に使用
                if 'transcript_summary' in result['source'] and result['source']['transcript_summary']:
                    context += f"詳細内容: {result['source']['transcript_summary']}\n"
                    print(f"📄 Added transcript summary for: {result['source']['title']}")
                
                if 'speakers' in result['source'] and result['source']['speakers']:
                    speaker_names = []
                    for speaker in result['source']['speakers']:
                        speaker_names.append(f"{speaker['name']}（{speaker['company']}）")
                    context += f"講演者: {', '.join(speaker_names)}\n"
                
                if 'track' in result['source']:
                    context += f"トラック: {result['source']['track']}\n"
                
                if 'date' in result['source'] and 'start_time' in result['source']:
                    context += f"開催日時: {result['source']['date']} {result['source']['start_time']}\n"
                
                context += "\n"
                
                # transcript有無の情報をSourceに追加
                source_title = result['source']['title']
                if result.get('has_transcript'):
                    source_title += " [詳細内容あり]"
                
                sources.append(Source(
                    title=source_title,
                    score=f"{result['score']:.4f}"
                ))
        else:
            context = "関連する参考資料が見つかりませんでした。一般的な知識で回答してください。\n\n"
        
        # 3. LLMプロンプト構築
        prompt = f"""{context}

質問: {message}

以下の点を守って日本語で回答してください：
- 必ず日本語で回答する
- 丁寧で分かりやすい表現を使う
- 参考資料がある場合は、その内容を基に回答する
- 詳細内容がある場合は、その情報を積極的に活用する
- 参考資料がない場合は、一般的な知識で回答する

回答:"""
        
        print(f"🤖 Generating response with context from {len(search_results)} sources")
        
        # 4. LLM回答生成の実行時間測定
        llm_response_start = time.time()
        llm_result = await bedrock_client.generate_guarded_response(prompt)
        llm_response_time = time.time() - llm_response_start
        
        print(f"🤖 LLM response generated in {llm_response_time:.3f}s")
        
        # 5. レスポンスの正規化
        final_response = llm_result.strip() if isinstance(llm_result, str) else str(llm_result)
        
        # 全体処理時間の計算
        total_time = time.time() - total_start
        
        # 合計LLM時間（キーワード抽出 + 回答生成）
        total_llm_time = llm_keyword_time + llm_response_time
        
        print(f"⏱️ Performance Summary:")
        print(f"   - OpenSearch time: {opensearch_time:.3f}s")
        print(f"   - LLM total time: {total_llm_time:.3f}s (keyword: {llm_keyword_time:.3f}s + response: {llm_response_time:.3f}s)")
        print(f"   - Total time: {total_time:.3f}s")
        
        return ChatResponse(
            success=True,
            response=final_response,
            sources=sources,
            context_used=len(search_results) > 0,
            debug={
                "search_results_count": len(search_results),
                "transcript_results_count": transcript_count,
                "guardrail_applied": False,
                "original_query": message,
                "optimized_query": search_query,
                "search_method": "hybrid_with_transcript",
                "performance": {
                    "opensearch_time": round(opensearch_time, 3),
                    "llm_time": round(total_llm_time, 3),
                    "llm_keyword_time": round(llm_keyword_time, 3),
                    "llm_response_time": round(llm_response_time, 3),
                    "total_time": round(total_time, 3)
                }
            }
        )
        
    except Exception as error:
        total_time = time.time() - total_start
        print(f"❌ Chat API error: {error} (total time: {total_time:.3f}s)")
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
