from app.inquiry.graph import inquiry_app

# Backward Compatibility (기존 코드와의 호환성을 위해 함수 래핑)
async def run_final_answer_stream(inputs):
    """
    Refactored Inquiry Agent Entry Point
    Legacy wrapper to maintain compatibility with existing UI calls.
    Now delegates all logic to the modular LangGraph app in `app.inquiry.graph`.
    """
    # LangGraph 실행 (Streaming)
    # inputs expected: {"question": str, "store_id": int, ...}
    async for event in inquiry_app.astream(inputs):
        yield event