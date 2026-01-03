# 📄 LLM 응답 포맷 전략 변경: JSON to Tag-based Parsing
**Date:** 2026-01-03  
**Author:** Antigravity (AI Architect)  
**Status:** Applied  

## 1. 배경 (Background) & 문제점 (Problem)

본 프로젝트의 리포트 생성 기능(`report_graph.py`)은 초기 설계 시 **JSON 포맷**을 통해 구조화된 데이터(분석 내용, 요약, 리스크 점수 등)를 LLM으로부터 수신하도록 설계되었습니다. 그러나 **마크다운(Markdown) 표와 복잡한 서술형 텍스트**를 JSON 값(Value)으로 포함시키는 과정에서 지속적인 파싱 오류가 발생했습니다.

### 주요 발생 에러 (Symptoms)
- `json.decoder.JSONDecodeError: Expecting ',' delimiter`: 문자열 내 따옴표(`"`) 이스케이프 실패.
- `Illegal trailing comma`: JSON 객체 마지막 항목 뒤에 불필요한 콤마 삽입.
- **마크다운 렌더링 깨짐**: JSON 표준 준수를 위해 개행 문자(`\n`)를 강제 치환하는 과정에서, 실제 UI 렌더링 시 줄바꿈이 소실되어 표(Table)나 리스트가 한 줄로 뭉개지는 현상.

### 원인 분석 (Root Cause)
LLM(Gemini) 입장에서 **"JSON 문법 준수(이스케이프)"**와 **"마크다운 문법 준수(가독성)"**라는 두 가지 상충되는 제약을 동시에 만족시키기 어렵습니다. 특히, 마크다운 표(`|---|---|`)나 줄바꿈이 포함된 긴 텍스트를 JSON 문자열로 변환할 때, `\`(백슬래시) 처리에서 환각(Hallucination)이나 오류가 빈번하게 발생합니다.

---

## 2. 해결 전략: Tag-based Parsing (태그 기반 파싱)

우리는 JSON의 엄격한 문법 제약을 우회하고, 텍스트 데이터의 무결성을 보장하기 위해 **XML 스타일의 커스텀 태그(Custom Tags) 방식**으로 설계를 변경했습니다. 이는 HTML 구조와 유사하지만, 훨씬 단순하고 목적 지향적인 포맷입니다.

### 변경 전 (JSON Approach)
```json
{
  "sales_analysis": "## 주간 분석\n\n| 항목 | 값 |\n|---|---|\n..."
}
```
> **Risk**: `"` 또는 `\n` 처리가 하나라도 빗나가면 전체 JSON 파싱이 실패함.

### 변경 후 (Tag-based Approach)
```text
<SECTION:SALES_ANALYSIS>
## 주간 분석

| 항목 | 값 |
|---|---|
...
</SECTION:SALES_ANALYSIS>
```
> **Benefit**: 태그 내부의 내용은 **Raw Text**로 취급되므로, 따옴표나 줄바꿈 이스케이프가 전혀 필요 없음.

---

## 3. 구현 상세 (Implementation Details)

### 3.1. 프롬프트 엔지니어링 (Prompt Engineering)
AI에게 더 이상 JSON 포맷을 강요하지 않고, 각 섹션을 명시적인 태그로 감싸도록 지시합니다.

```python
prompt = """
응답은 반드시 아래 태그 형식을 사용하여 작성할 것 (JSON 아님):

<SECTION:SALES_ANALYSIS>
(마크다운 표와 분석 내용...)
</SECTION:SALES_ANALYSIS>

<SECTION:SUMMARY>
(요약 내용...)
</SECTION:SUMMARY>
...
"""
```

### 3.2. 파서 로직 (Parser Logic)
Python의 표준 라이브러리인 `re`(Regular Expression)를 사용하여 각 태그 사이의 콘텐츠를 강력하게 추출합니다.

```python
import re

def extract_section(tag, text):
    # DOTALL 플래그를 사용하여 줄바꿈을 포함한 모든 텍스트 매칭
    pattern = f"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    # 양쪽 공백 제거 후 반환
    return match.group(1).strip() if match else ""
```

---

## 4. 기대 효과 (Expected Outcomes)

1.  **파싱 안정성 극대화 (Robustness)**: JSON 문법 오류로 인한 리포트 생성 실패율이 **0%에 수렴**할 것으로 예상됩니다.
2.  **마크다운 호환성 (Compatibility)**: AI가 생성한 마크다운 표, 리스트, 이모지 등이 별도의 후처(Post-processing) 없이 UI에 완벽하게 렌더링됩니다.
3.  **유지보수 용이성 (Maintainability)**: 복잡한 정규식(제어 문자 제거 등)이나 외부 라이브러리(`dirtyjson`) 의존성을 제거하고, 직관적인 태그 추출 로직으로 관리할 수 있습니다.

---

**Note**: 이 아키텍처 변경은 LLM이 생성하는 **"비정형 텍스트(Analysis)"**와 **"정형 데이터(Metrics)"**를 분리하여 처리하는 **Hybrid Parsing Strategy**의 일환입니다.
