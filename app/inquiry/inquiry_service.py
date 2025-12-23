from app.core.db import SessionLocal
from app.inquiry.inquiry_schema import StoreInquiry

def save_inquiry(store_id: int, category: str, question: str, answer: str) -> int:
    """
    질문과 AI 답변을 DB에 저장
    
    Args:
        store_id: 매장 ID
        category: 질문 카테고리 (sales/manual/policy)
        question: 질문 내용
        answer: AI 답변
    
    Returns:
        생성된 inquiry_id
    """
    db = SessionLocal()
    try:
        new_inquiry = StoreInquiry(
            store_id=store_id,
            category=category,
            question=question,
            answer=answer
        )
        db.add(new_inquiry)
        db.commit()
        db.refresh(new_inquiry)
        return new_inquiry.inquiry_id
    finally:
        db.close()
