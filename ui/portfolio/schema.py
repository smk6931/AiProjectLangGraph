import streamlit as st

def render_schema():
    st.header("4. 💾 Database Schema")
    st.caption("PostgreSQL + pgvector Hybrid Architecture")

    # --- Strategy Explanation ---
    st.info("""
    **Single DB Strategy**:
    별도의 Vector DB(Pinecone, Milvus 등)를 구축하지 않고, **PostgreSQL 하나로** 
    관계형 데이터(매출/주문)와 비정형 데이터(리뷰/매뉴얼 벡터)를 통합 관리합니다.
    이로 인해 **데이터 일관성(Consistency)** 유지와 **조인(Join) 연산**이 획기적으로 간편해졌습니다.
    """)

    # --- ERD Diagram ---
    st.markdown("### 🗺️ Entity Relationship Diagram (ERD)")
    
    # Graphviz Code
    st.graphviz_chart("""
    digraph ERD {
        rankdir=LR;
        node [shape=box, style=filled, fillcolor="white", fontname="Arial"];
        edge [fontname="Arial"];

        # Entities
        subgraph cluster_store {
            label = "Store Domain";
            style = dashed;
            Stores [label="{Stores|PK store_id\lname\lregion\lcity}", shape=record, fillcolor="#E6F3FF"];
            Sales [label="{Sales_Daily|PK sales_id\lFK store_id\ldate\lrevenue\lweather}", shape=record];
        }

        subgraph cluster_menu {
            label = "Menu Domain";
            style = dashed;
            Menus [label="{Menus|PK menu_id\lname\lcategory\lprice\lvector embedding (1536d)}", shape=record, fillcolor="#FFE6E6"];
        }

        subgraph cluster_order {
            label = "Order & Review";
            style = dashed;
            Orders [label="{Orders|PK order_id\lFK store_id\lFK menu_id\lquantity}", shape=record];
            Reviews [label="{Reviews|PK review_id\lFK store_id\lFK order_id\lrating\ltext\lvector embedding}", shape=record, fillcolor="#E6FFE6"];
        }

        subgraph cluster_ai {
            label = "AI & Knowledge";
            style = dashed;
            Reports [label="{Store_Reports|PK report_id\lFK store_id\ljson_content\lrisk_score}", shape=record, fillcolor="#FFF0E0"];
            Manuals [label="{Manuals|PK manual_id\lcategory\lcontent\lvector embedding}", shape=record, fillcolor="#FFF0E0"];
        }

        # Relationships
        Stores -> Sales [label="1:N", color="#666666"];
        Stores -> Orders [label="1:N", color="#666666"];
        Stores -> Reviews [label="1:N", color="#666666"];
        Stores -> Reports [label="1:N", color="#666666"];

        Menus -> Orders [label="1:N", color="#666666"];
        Menus -> Reviews [label="1:N", color="#666666"];

        Orders -> Reviews [label="1:1 (Optional)", style=dotted, color="#999999"];
    }
    """)

    st.divider()

    # --- Table Details (Two Columns) ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📌 Key Tables")
        st.markdown("""
        **1. Stores (가맹점)**
        - 가맹점의 메타 정보 (위치, 인구밀도 지수 등)
        
        **2. Sales_Daily (일별 매출)**
        - AI 분석의 기초가 되는 시계열 데이터
        - 날씨 태그(`weather_info`) 포함
        
        **3. Menus (메뉴)**
        - `embedding`: 메뉴 설명에 대한 벡터값 저장 (유사 메뉴 검색용)
        """)

    with col2:
        st.subheader("🧠 Vector Tables (AI)")
        st.markdown("""
        **4. Reviews (리뷰 + 벡터)**
        - `embedding`: 고객 리뷰의 감정/의미 벡터
        - "맛은 있는데 비싸요" 같은 뉘앙스 검색 가능
        
        **5. Manuals (매뉴얼 + 벡터)**
        - 가맹점 운영 매뉴얼 Chunk 저장
        - RAG(검색 증강 생성) 시스템의 지식 베이스
        """)

    with st.expander("🔍 보너스: 왜 Hybrid DB인가요?"):
        st.write("""
        만약 Vector DB를 따로 썼다면?
        1. 리뷰가 등록될 때 RDB에 저장하고, Vector DB에도 Sync를 맞춰야 함 (**이중 관리**)
        2. "강남점의(RDB) 긍정적인 리뷰(Vector)만 찾아줘" 같은 쿼리가 매우 복잡해짐
        3. **pgvector**를 쓰면 SQL 한 줄로 이 모든 게 해결됨!
        """)
