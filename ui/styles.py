import streamlit as st

def apply_custom_styles():
    """
    포트폴리오용 프리미엄 CSS 스타일 적용
    - 폰트: Pretendard
    - 테마: Modern Dark AI Dashboard
    """
    st.markdown("""
        <style>
            /* 1. 웹폰트 로드 (Pretendard) */
            @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.8/dist/web/static/pretendard.css");

            html, body, [class*="css"] {
                font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif !important;
            }

            /* 2. 전체 배경 및 메인 컨테이너 */
            .stApp {
                background-color: #0E1117; /* Deep Dark Background */
            }
            
            /* Sidebar 스타일 */
            [data-testid="stSidebar"] {
                background-color: #161B22;
                border-right: 1px solid #30363D;
            }

            /* 3. 헤더 타이틀 스타일 (그라디언트 텍스트) */
            h1 {
                background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 800 !important;
                letter-spacing: -0.02em;
                margin-bottom: 0.5rem !important;
            }
            
            /* 4. Expander (아코디언) 스타일 Upgrade */
            .streamlit-expanderHeader {
                background-color: #1F242C !important;
                border-radius: 10px !important;
                border: 1px solid #30363D !important;
                color: #E6EDF3 !important;
                font-size: 15px !important;
                font-weight: 600 !important;
                transition: all 0.2s ease-in-out;
            }
            .streamlit-expanderHeader:hover {
                border-color: #4facfe !important;
                color: #4facfe !important;
            }
            .streamlit-expanderContent {
                background-color: #161B22 !important;
                border: 1px solid #30363D;
                border-top: none;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                padding: 1rem !important;
            }
            
            /* Expander 내부의 못생긴 화살표 아이콘 숨기기/교체 */
            /* Streamlit 구조상 완벽 제어는 어렵지만 최대한 숨김 */
            .streamlit-expanderHeader svg {
                display: none !important; /* 기본 아이콘 숨김 */
            }
            .streamlit-expanderHeader::after {
                content: "🔽"; /* 대체 아이콘 */
                margin-left: auto;
                font-size: 12px;
                opacity: 0.7;
            }

            /* 5. Chat Message (말풍선) 스타일 */
            [data-testid="stChatMessage"] {
                background-color: transparent !important;
                padding: 1rem 0;
            }
            /* User Message */
            [data-testid="stChatMessage"][data-testid="user"] {
                flex-direction: row-reverse;
            }
            [data-testid="chatAvatarIcon-user"] {
                background-color: #4facfe !important;
            }
            
            /* AI Message Container (내용 박스) */
            div[data-testid="stChatMessageContent"] {
                background-color: #1F242C;
                border: 1px solid #30363D;
                border-radius: 16px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }

            /* 6. Custom Card Styling (HTML/CSS로 직접 그리는 요소들) */
            .metric-card {
                background: linear-gradient(135deg, #1F242C 0%, #161B22 100%);
                border: 1px solid #30363D;
                border-radius: 12px;
                padding: 16px;
                text-align: center;
                transition: transform 0.2s;
            }
            .metric-card:hover {
                transform: translateY(-2px);
                border-color: #4facfe;
            }
            .metric-label {
                font-size: 0.85rem;
                color: #8B949E;
                margin-bottom: 4px;
            }
            .metric-value {
                font-size: 1.5rem;
                font-weight: 700;
                color: #E6EDF3;
            }
            .metric-delta {
                font-size: 0.8rem;
                font-weight: 600;
            }
            .delta-up { color: #3FB950; }
            .delta-down { color: #FF7B72; }

            /* 7. Button Style (Primary) */
            div.stButton > button:first-child {
                background: linear-gradient(90deg, #2563EB 0%, #1D4ED8 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                padding: 0.5rem 1rem;
                transition: all 0.2s;
            }
            div.stButton > button:first-child:hover {
                background: linear-gradient(90deg, #1D4ED8 0%, #1E40AF 100%);
                box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
                transform: scale(1.02);
            }
            /* Secondary Button (Outline) */
            div[data-testid="stForm"] button, div.stButton > button.secondary {
                background: transparent;
                border: 1px solid #30363D;
                color: #E6EDF3;
            }

            /* 10. 가독성 개선 (Bright Text Mode) */
            p, li, span, div {
                color: #E6EDF3; /* 기본 텍스트를 밝은 회색/흰색에 가깝게 */
                line-height: 1.6;
            }
            
            /* 헤더 가독성 강화 */
            h1, h2, h3, h4, h5, h6 {
                color: #FFFFFF !important;
            }
            
            /* Metric Label도 좀 더 밝게 */
            .metric-label {
                color: #C9D1D9 !important;
            }
            
            /* 모바일 대응 (반응형) */
            @media (max-width: 768px) {
                html, body, [class*="css"] {
                    font-size: 16px !important; /* 기본 폰트 사이즈 Up */
                }
                
                h1 {
                    font-size: 1.8rem !important;
                }
                h2 {
                    font-size: 1.5rem !important;
                }
                h3 {
                    font-size: 1.3rem !important;
                }
                
                /* 모바일에서 카드 패딩 축소 */
                .metric-card {
                    padding: 12px !important;
                }
                .metric-value {
                    font-size: 1.3rem !important;
                }
                
                /* 버튼 터치 영역 확보 */
                div.stButton > button {
                    min-height: 50px; 
                    font-size: 1rem !important;
                }
                
                /* 입력창 텍스트 진하게 */
                input, textarea {
                    color: #FFFFFF !important;
                    font-weight: 500 !important;
                }
            }
        </style>
    """, unsafe_allow_html=True)

def show_metric_card(col, label, value, delta=None):
    """
    Custom HTML Metric Card
    Streamlit 기본 st.metric보다 예쁜 카드 형태
    """
    delta_html = ""
    if delta:
        color_class = "delta-up" if "+" in str(delta) or float(str(delta).replace("%","").replace(",","")) > 0 else "delta-down"
        delta_html = f'<div class="metric-delta {color_class}">{delta}</div>'
    
    html = f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """
    col.markdown(html, unsafe_allow_html=True)
