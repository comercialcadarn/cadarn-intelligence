import streamlit as st

LOGO_BASE64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAMAAABF0y+mAAAAUVBMVEVHcEzXzOlUMpliQ6FMJ5Te1e1OKZVMJpSAZ7NKJJNdPZ5mSKKGbrZJIpNePp5pTKRrT6VKI5OciMOFbLZ6Ya9WNJrr4vZzWap6YK6lksqHbreDBgMvAAAAG3RSTlMAJcm2OTr//1L/3PNz//zd1f9YQJP/CK26QCfR2khpAAAAo0lEQVR4AXXLBQ7EAAwDwRR9LjP9/6FXxsRCa7SyznFd15Fjnuv6ci0IEQbH+YEwMSJM/AE2RrRxDm2MCVqYpEBGA2MyLwxMSrCyMCNjyXWcQ1QWZkQkBiYEagszMBIDmxRhrSFbp8vIQjRM+yNU8Ag1xLCGo4pz2GIOVZzDcg51nEOkc6ihSEOEk4FdCHhiYF/OoYFOSx7hjOkTXdc9Q+mP8wd7Owtgvc9xfgAAAABJRU5ErkJggg=="

def alternar_tema():
    st.session_state.tema_escuro = not st.session_state.tema_escuro

def renderizar_css_e_particulas():
    vars_css = """
        --bg-color: #0b0b0b; --card-bg: rgba(18, 18, 18, 0.85); --text-main: #e0e0e0;
        --text-muted: #a0a0a0; --border-color: rgba(255, 255, 255, 0.08); --title-color: white;
        --log-bg: #0b0b0b; --log-text: #00ffa3; --step-active: #832eff; --step-inactive: #333;
        --badge-done-color: #00ffa3; --btn-disabled-bg: #2a2a2a; --btn-disabled-color: #666666;
    """ if st.session_state.tema_escuro else """
        --bg-color: #f4f6f9; --card-bg: rgba(255, 255, 255, 0.95); --text-main: #1e1e1e;
        --text-muted: #666666; --border-color: rgba(0, 0, 0, 0.1); --title-color: #121212;
        --log-bg: #f8f9fa; --log-text: #008a55; --step-inactive: #ddd; --step-active: #6b15eb;
        --badge-done-color: #008a55; --btn-disabled-bg: #e0e0e0; --btn-disabled-color: #9e9e9e;
    """

    st.markdown(f"""
        <style>
        /* CSS da Navegação (Pills) */
        div[data-testid="stRadio"] {{ display: none !important; }}
        .nav-pill-bar {{ display: flex; gap: 8px; justify-content: center; margin-bottom: 12px; }}
        .nav-pill {{ padding: 8px 24px; border-radius: 999px; font-weight: 600; font-size: 0.85rem;
            border: 1px solid rgba(131,46,255,0.4); cursor: pointer; color: var(--text-muted);
            background: transparent; transition: all 0.25s ease; letter-spacing: 1px; }}
        .nav-pill.active {{ background: linear-gradient(135deg,#832eff,#6b15eb);
            color: white; border-color: transparent; box-shadow: 0 0 18px rgba(131,46,255,0.5); }}

        /* CSS Global Premium */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@200;400;600&display=swap');
        * {{ font-family: 'Outfit', sans-serif; transition: background-color 0.3s, color 0.3s; }}
        :root {{ {vars_css} }}
        .block-container {{ padding-top: 1.5rem !important; }}
        header[data-testid="stHeader"] {{ display: none !important; }}
        .stApp {{ background-color: var(--bg-color); background-image: linear-gradient(rgba(131, 46, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(131, 46, 255, 0.03) 1px, transparent 1px); background-size: 30px 30px; color: var(--text-main); }}
        [data-testid="stAppViewContainer"] p, [data-testid="stAppViewContainer"] h1, [data-testid="stAppViewContainer"] h2, [data-testid="stAppViewContainer"] h3, [data-testid="stWidgetLabel"] p, [data-testid="stMetricValue"] div, [data-testid="stMetricLabel"] p, [data-testid="stExpander"] p, .stCheckbox label p, .stRadio label p {{ color: var(--text-main) !important; }}
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background: var(--card-bg) !important; border: 1px solid rgba(131, 46, 255, 0.2) !important;
            border-radius: 16px !important; backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            box-shadow: 0 8px 40px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.07) !important;
            padding: 24px !important; transition: box-shadow 0.3s ease, border-color 0.3s ease !important;
        }}
        [data-testid="stVerticalBlockBorderWrapper"]:hover {{
            border-color: rgba(131, 46, 255, 0.5) !important;
            box-shadow: 0 8px 40px rgba(131,46,255,0.15), inset 0 1px 0 rgba(255,255,255,0.07) !important;
        }}
        .stButton>button {{ 
            background: linear-gradient(135deg, #832eff 0%, #6b15eb 100%) !important; 
            color: white !important; border: none !important; padding: 14px 28px !important; 
            border-radius: 8px !important; font-weight: 600 !important; width: 100%; 
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important; 
            position: relative; overflow: hidden; z-index: 1;
        }}
        .stButton>button::after {{
            content: ""; position: absolute; top: 0; left: -100%; width: 100%; height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: left 0.6s ease; pointer-events: none; z-index: 5;
        }}
        .stButton>button:hover::after {{ left: 100%; }}
        .stButton>button:hover {{ box-shadow: 0 10px 25px rgba(131,46,255,0.5) !important; transform: translateY(-2px) !important; }}
        .stButton>button:disabled {{ opacity: 0.4 !important; background: var(--btn-disabled-bg) !important; color: var(--btn-disabled-color) !important; box-shadow: none !important; transform: none !important; }}
        .theme-toggle-btn {{ background: transparent !important; color: var(--text-main) !important; border: 1px solid var(--border-color) !important; padding: 5px 10px !important; border-radius: 20px !important; width: auto !important; float: right; }}
        .btn-reset {{ background: transparent !important; color: #ff4b4b !important; border: 1px solid #ff4b4b !important; }}
        .btn-reset:hover {{ background: rgba(255, 75, 75, 0.1) !important; }}
        .logo-container {{ text-align: center; padding: 0px 0 20px 0; }}
        .main-logo {{ width: 80px; filter: drop-shadow(0 0 20px rgba(131, 46, 255, 0.6)); margin-bottom: 5px; }}
        @keyframes gradientShift {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}
        .glitch-title {{ font-size: 2rem; font-weight: 600; margin-bottom: 0; background: linear-gradient(270deg, #ffffff, #832eff, #00ffa3, #832eff); background-size: 400% 400%; -webkit-background-clip: text; -webkit-text-fill-color: transparent; animation: gradientShift 6s ease infinite; }}
        .sub-title {{ color: #832eff; font-weight: 600; letter-spacing: 4px; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; }}
        .stepper-wrapper {{ display: flex; justify-content: space-between; margin-top: 20px; padding-bottom: 15px; position: relative; }}
        .stepper-item {{ display: flex; flex-direction: column; align-items: center; flex: 1; position: relative; }}
        .stepper-item::before, .stepper-item::after {{ position: absolute; content: ""; border-bottom: 2px solid var(--step-inactive); width: 100%; top: 15px; z-index: 2; }}
        .stepper-item::before {{ left: -50%; }} .stepper-item::after {{ left: 50%; }}
        .stepper-item:first-child::before, .stepper-item:last-child::after {{ content: none; }}
        .stepper-item .step-counter {{ position: relative; z-index: 5; display: flex; justify-content: center; align-items: center; width: 30px; height: 30px; border-radius: 50%; background: var(--step-inactive); color: white; font-weight: bold; font-size: 14px; margin-bottom: 8px; transition: 0.3s; }}
        @keyframes pulse-ring {{ 0% {{ box-shadow: 0 0 0 0 rgba(131,46,255, 0.6); }} 70% {{ box-shadow: 0 0 0 10px rgba(131,46,255, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(131,46,255, 0); }} }}
        .stepper-item.active .step-counter {{ background: var(--step-active); box-shadow: 0 0 14px var(--step-active); animation: pulse-ring 1.5s ease-out infinite; }}
        .stepper-item.completed .step-counter {{ background: #00ffa3; color: #0b0b0b; }}
        .stepper-item.completed::before, .stepper-item.active::before {{ border-color: #00ffa3; }}
        .step-name {{ font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-align: center; text-transform: uppercase; }}
        .stepper-item.active .step-name {{ color: var(--step-active); }}
        .file-meta {{ font-size: 0.8rem; color: #832eff; font-weight: 600; margin-top: -10px; margin-bottom: 15px; }}
        .history-card {{ padding: 15px; border-radius: 8px; border: 1px solid var(--border-color); background: rgba(131, 46, 255, 0.05); margin-bottom: 15px; }}
        [data-testid="stFileUploader"] {{ border: 2px dashed rgba(131, 46, 255, 0.4) !important; border-radius: 12px !important; padding: 12px !important; background: rgba(131, 46, 255, 0.04) !important; transition: all 0.3s ease !important; }}
        [data-testid="stFileUploader"]:hover {{ border-color: #832eff !important; background: rgba(131, 46, 255, 0.09) !important; box-shadow: 0 0 20px rgba(131,46,255,0.2) !important; }}
        [data-testid="stFileUploadDropzone"] {{ background: transparent !important; }}
        </style>
        <canvas id="particle-canvas" style="position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;opacity:0.35;"></canvas>
        <script>
        const canvas = document.getElementById('particle-canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const particles = Array.from({{length: 55}}, () => ({{
          x: Math.random()*canvas.width, y: Math.random()*canvas.height,
          r: Math.random()*2+0.5, dx: (Math.random()-0.5)*0.4, dy: (Math.random()-0.5)*0.4,
          alpha: Math.random()*0.5+0.2
        }}));
        function draw() {{
          ctx.clearRect(0,0,canvas.width,canvas.height);
          particles.forEach(p => {{
            ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
            ctx.fillStyle = `rgba(131,46,255,${{p.alpha}})`; ctx.fill();
            p.x+=p.dx; p.y+=p.dy;
            if(p.x<0||p.x>canvas.width) p.dx*=-1;
            if(p.y<0||p.y>canvas.height) p.dy*=-1;
          }});
          requestAnimationFrame(draw);
        }}
        draw();
        </script>
    """, unsafe_allow_html=True)

def renderizar_cabecalho():
    col_vazia, col_tema = st.columns([10, 1.5])
    with col_tema:
        icone_tema = "☀️ Claro" if st.session_state.tema_escuro else "🌙 Escuro"
        st.button(icone_tema, on_click=alternar_tema, key="btn_tema")
        st.markdown("<script>window.parent.document.querySelector('.stButton button').classList.add('theme-toggle-btn');</script>", unsafe_allow_html=True)

    st.markdown(f"""
        <div class="logo-container">
            <img src="{LOGO_BASE64}" class="main-logo">
            <p class="sub-title">Cadarn Intelligence</p>
            <h1 class="glitch-title">ENRIQUECIMENTO DE DADOS</h1>
        </div>
    """, unsafe_allow_html=True)

def render_stepper(status):
    c = ["completed" if status > i else "active" if status == i else "" for i in range(1, 5)]
    st.markdown(f"""
    <div class="stepper-wrapper">
        <div class="stepper-item {c[0]}"><div class="step-counter">1</div><div class="step-name">Aguardando</div></div>
        <div class="stepper-item {c[1]}"><div class="step-counter">2</div><div class="step-name">Carregado</div></div>
        <div class="stepper-item {c[2]}"><div class="step-counter">3</div><div class="step-name">Processando</div></div>
        <div class="stepper-item {c[3]}"><div class="step-counter">4</div><div class="step-name">Concluído</div></div>
    </div>
    """, unsafe_allow_html=True)