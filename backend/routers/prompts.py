from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.prompt_service import prompt_service

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

class OptimizeRequest(BaseModel):
    prompt: str
    tag_length: Optional[str] = None # "short", "long", "very_short", "very_long"

class OptimizeResponse(BaseModel):
    optimized_prompt: str

@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_prompt(request: OptimizeRequest):
    try:
        from config import get_config
        config = get_config()
        tag_length = request.tag_length or config.get("tipo_tag_length", "long")
        optimized = prompt_service.optimize_prompt(request.prompt, tag_length=tag_length)
        return OptimizeResponse(optimized_prompt=optimized)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
