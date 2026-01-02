import json
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
# [Refactoring] 분리된 노드들 Import (Clean Architecture)
from app.inquiry.inquiry_schema import InquiryState
from app.inquiry.nodes.router import router_node
from app.inquiry.nodes.sales import diagnosis_node
from app.inquiry.nodes.retrieval import manual_node, policy_node, web_search_node
from app.inquiry.nodes.answer import answer_node_v2
from app.inquiry.nodes.save import save_node
from app.clients.genai import genai_generate_text


# ===== [Phase 1] 검색 및 진단 실행 함수 (Entry Point) =====
async def run_search_check(store_id: int, question: str) -> Dict[str, Any]:
    """
    1단계: 질문 분류 -> DB 검색 -> 유사도 평가 결과 반환
    """
    # 1. State 초기화
    state = InquiryState(
        store_id=store_id,
        question=question,
        category="",
        sales_data={},
        manual_data=[],
        policy_data=[],
        final_answer="",
        inquiry_id=0,
        diagnosis_result=""
    )
    
    # 2. Router 실행
    state = await router_node(state)
    category = state["category"]
    
    # 3. 카테고리별 검색 실행
    top_doc = None
    min_dist = 1.0 
    search_results = []
    
    if category == "sales":
        # 매출은 사용자가 선택할 필요 없이 무조건 데이터 분석
        state = await diagnosis_node(state)
        min_dist = 0.0
        sales_info = state.get("sales_data", {})
        top_doc = {
            "title": "매출 데이터 분석", 
            "content": sales_info.get("summary_text", "분석 결과 없음"),
            "search_params": {
                "scope": sales_info.get("scope"),
                "tables_used": sales_info.get("tables_used"),
                "period": sales_info.get("period")
            }
        }
        
    elif category == "manual":
        # 매뉴얼 검색 실행
        state = await manual_node(state)
        docs = state.get("manual_data", [])
        meta = state.get("search_meta", {})
        min_dist = meta.get("min_distance", 1.0)
        
        if docs:
            first_line = docs[0].split("\n")[0]
            content_preview = docs[0][len(first_line)+1:]
            top_doc = {"title": first_line, "content": content_preview[:200] + "..."}
            search_results = docs 

    elif category == "policy":
        # 정책 검색 실행
        state = await policy_node(state)
        docs = state.get("policy_data", [])
        meta = state.get("search_meta", {})
        min_dist = meta.get("min_distance", 1.0)
        
        if docs:
            first_line = docs[0].split("\n")[0]
            content_preview = docs[0][len(first_line)+1:]
            top_doc = {"title": first_line, "content": content_preview[:200] + "..."}
            search_results = docs

    # [Feature] AI Contextual Check: 문서 적합성 판단
    recommendation = {"indices": [], "comment": ""}
    
    if search_results and category != "sales":
        try:
            # 후보군 제목 + 앞부분 요약 추출
            docs_summary = []
            for i, c in enumerate(search_results):
                lines = c.split('\n')
                title = lines[0]
                preview = lines[1][:50] + "..." if len(lines) > 1 else ""
                docs_summary.append(f"[{i}] {title} ({preview})")
            
            rec_prompt = f"""
            질문: "{question}"
            
            검색된 문서 목록:
            {json.dumps(docs_summary, ensure_ascii=False, indent=2)}
            
            위 문서들이 질문에 답변하기에 '충분히 관련성'이 있는지 판단하세요.
            [Output Format]
            JSON으로만 응답하세요:
            {{
                "relevant_indices": [0, 2],  // 관련 문서 번호 (없으면 [])
                "reason": "판단 이유"
            }}
            """
            # 간단 추천 로직 (일단 간소화)
            rec_res = await genai_generate_text(rec_prompt)
            clean_json = rec_res.replace("```json", "").replace("```", "").strip()
            rec_data = json.loads(clean_json)
            
            relevant_indices = rec_data.get("relevant_indices", [])
            reason = rec_data.get("reason", "")
            
            if relevant_indices:
                recommendation["indices"] = relevant_indices
                recommendation["comment"] = f"✅ AI 추천: {reason}"
            else:
                recommendation["indices"] = []
                recommendation["comment"] = f"⚠️ AI 판단: {reason}"
                
        except Exception as e:
            print(f"⚠️ 추천 로직 에러: {e}")
            recommendation["comment"] = "추천 시스템 일시 오류"

    return {
        "category": category,
        "min_distance": min_dist,
        "similarity_score": round((1 - min_dist) * 100, 1),
        "top_document": top_doc,
        "candidates": search_results,
        "context_data": search_results if category != "sales" else [],
        "recommendation": recommendation,
        "sales_data": state.get("sales_data", {})
    }


# ===== [Phase 2] 최종 답변 생성 스트리밍 (Entry Point) =====
async def run_final_answer_stream(store_id: int, question: str, category: str, mode: str, context_data: list):
    """
    2단계: 사용자 선택(DB/Web)에 따라 답변 생성
    mode: 'db' (기존 데이터 사용) | 'web' (웹 검색 수행)
    """
    
    yield json.dumps({"step": "init", "message": f"🚀 {mode.upper()} 모드로 답변 생성 시작..."}) + "\n"
    
    state = InquiryState(
        store_id=store_id, 
        question=question, 
        category=category,
        sales_data={}, manual_data=[], policy_data=[], final_answer="", inquiry_id=0, diagnosis_result=""
    )

    if category == "sales": # Sales Logic
        # [Optimization] Phase 1에서 넘어온 데이터가 있으면 재사용 (LLM/DB 비용 절감)
        if context_data and isinstance(context_data[0], dict):
             yield json.dumps({"step": "sales", "message": "♻️ 기존 분석 데이터 활용 중..."}) + "\n"
             state["sales_data"] = context_data[0]
        else:
             yield json.dumps({"step": "sales", "message": "📉 매출 데이터 분석 중..."}) + "\n"
             state = await diagnosis_node(state)
        
        details = {
            "type": "analysis", 
            "summary": state["sales_data"].get("diagnosis_result"),
            "sales_summary": state["sales_data"].get("summary_text", "")[:100] + "..."
        }
        yield json.dumps({"step": "sales", "message": "✅ 분석 완료", "details": details}) + "\n"
        
    else: # Retrieval Logic
        if mode == "web":
            yield json.dumps({"step": "web_search", "message": "🌐 외부 웹 검색 수행 중..."}) + "\n"
            state = await web_search_node(state)
            
            web_res = state["manual_data"][0] if state["manual_data"] else ""
            details = {"type": "web_result", "content": web_res}
            yield json.dumps({"step": "web_search", "message": "✅ 외부 정보 수집 완료", "details": details}) + "\n"
        else:
            # Context Restore
            key = "manual_data" if category == "manual" else "policy_data"
            state[key] = context_data
            yield json.dumps({"step": "check", "message": "📚 내부 DB 데이터 활용"}) + "\n"

    # Answer Generation
    yield json.dumps({"step": "answer", "message": "✍️ 답변 작성 중..."}) + "\n"
    state = await answer_node_v2(state)
    
    # Save
    yield json.dumps({"step": "save", "message": "💾 기록 저장 중..."}) + "\n"
    state = await save_node(state)
    
    yield json.dumps({
        "step": "done",
        "message": "처리가 완료되었습니다.",
        "final_answer": state["final_answer"],
        "category": state["category"]
    }) + "\n"