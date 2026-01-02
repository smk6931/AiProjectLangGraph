from app.inquiry.inquiry_schema import InquiryState
from app.inquiry.inquiry_service import save_inquiry

# ===== Step 7: Save Node (DB 저장) =====
async def save_node(state: InquiryState) -> InquiryState:
    """질문과 답변을 DB에 저장"""
    inquiry_id = save_inquiry(
        store_id=state["store_id"],
        category=state["category"],
        question=state["question"],
        answer=state["final_answer"]
    )
    
    state["inquiry_id"] = inquiry_id
    print(f"💾 [Save] DB 저장 완료 (ID: {inquiry_id})")
    
    return state
