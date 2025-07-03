from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router
from app.api import chat, debug  # debug をインポート

# FastAPIアプリを作成
app = FastAPI(
    title="AWS Summit RAG API",
    description="Phase 2: Advanced RAG System", 
    version="2.0.0"
)

# CORS設定（Next.jsからアクセスできるように）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# チャットAPIルーターを追加
app.include_router(chat_router, prefix="/api/v2", tags=["chat"])

# 動作確認用のエンドポイント
@app.get("/")
async def root():
    return {
        "message": "AWS Summit RAG API v2.0",
        "status": "running",
        "phase": "Phase 2: Advanced RAG"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "fastapi"}

app.include_router(chat.router)
app.include_router(debug.router)  # この行を追加
