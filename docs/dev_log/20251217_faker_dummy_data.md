# Faker를 활용한 더미 데이터 생성 자동화

## 📅 생성 일시
2025-12-17

## 🛠️ 주요 라이브러리 및 도구
- **Faker**: 한국어(`ko_KR`) 로케일을 지원하는 강력한 테스트 데이터 생성 라이브러리
- **SQLAlchemy**: Python ORM을 사용하여 DB 레코드 객체 생성 및 저장
- **AsyncIO**: (본 스크립트에서는 동기 세션을 사용했으나, 프로젝트 전반적으로 비동기 환경 고려)

## 📋 구현 내용 요약
기존에는 일일이 `INSERT INTO` 쿼리를 작성하여 테스트 데이터를 넣어야 했으나, `seed_data.py` 스크립트를 통해 이를 자동화했습니다.
이를 통해 개발 초기 단계에서 UI 테스트나 로직 검증에 필요한 기본 데이터셋을 손쉽게 확보할 수 있습니다.

### 1. 매장(Store) 데이터 생성 트릭
- 단순히 랜덤 문자열을 넣는 것이 아니라, 실제 존재하는 도시 이름과 대략적인 위경도 좌표를 매핑하여 **지도(Map) 기능 테스트 시** 어색하지 않도록 구성했습니다.
- `population_density_index` 같은 분석용 지표는 `random.uniform()`을 사용하여 다양성을 부여했습니다.

### 2. 메뉴(Menu) 데이터 구조화
- 카테고리(`coffee`, `dessert`)를 구분하여 생성했습니다.
- 원가(`cost_price`)는 정가(`list_price`)의 약 30% 수준으로 자동 계산되도록 로직을 추가하여, 추후 **마진율 분석** 시 현실적인 데이터가 나오도록 유도했습니다.

## 💻 실행 방법
프로젝트 루트 경로에서 다음 명령어 실행:
```powershell
.\.venv\Scripts\python seed_data.py
```
*사전에 `pip install faker` 설치 필요*

## 📝 코드 스니펫 (seed_data.py 핵심)
```python
# Faker 초기화 (한국어 설정)
fake = Faker('ko_KR')

# 중복 방지를 위한 체크 로직
exists = session.query(Store).filter_by(store_name=data["name"]).first()
if not exists:
    store = Store(...)
    session.add(store)
```
