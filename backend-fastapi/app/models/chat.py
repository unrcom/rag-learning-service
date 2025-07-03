from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatRequest(BaseModel):
    message: str

class Source(BaseModel):
    title: str
    score: str

class ChatResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    sources: Optional[List[Source]] = None
    context_used: bool = False
    debug: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
