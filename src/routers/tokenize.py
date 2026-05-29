from fastapi import APIRouter
from src.schemas.tokenize import TokenizeRequest, TokenizeResponse
from src.services import tokenizer_service

router = APIRouter(prefix="/tokenize", tags=["Tokenize"])


@router.post("", response_model=TokenizeResponse)
def tokenize_text(request: TokenizeRequest):
    return tokenizer_service.tokenize(
        model_or_encoding=request.model,
        text=request.text,
        include_tokens=request.include_tokens,
        include_token_ids=request.include_token_ids,
    )
