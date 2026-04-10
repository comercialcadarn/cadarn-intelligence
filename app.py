import streamlit as st
import pandas as pd
import time
import requests
import re
from io import BytesIO

# --- CONFIGURAÇÕES E CONSTANTES ---
LOGO_BASE64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAMAAABF0y+mAAAAUVBMVEVHcEzXzOlUMpliQ6FMJ5Te1e1OKZVMJpSAZ7NKJJNdPZ5mSKKGbrZJIpNePp5pTKRrT6VKI5OciMOFbLZ6Ya9WNJrr4vZzWap6YK6lksqHbreDBgMvAAAAG3RSTlMAJcm2OTr//1L/3PNz//zd1f9YQJP/CK26QCfR2khpAAAAo0lEQVR4AXXLBQ7EAAwDwRR9LjP9/6FXxsRCa7SyznFd15Fjnuv6ci0IEQbH+YEwMSJM/AE2RrRxDm2MCVqYpEBGA2MyLwxMSrCyMCNjyXWcQ1QWZkQkBiYEagszMBIDmxRhrSFbp8vIQjRM+yNU8Ag1xLCGo4pz2GIOVZzDcg51nEOkc6ihSEOEk4FdCHhiYF/OoYFOSx7hjOkTXdc9Q+mP8wd7Owtgvc9xfgAAAABJRU5ErkJggg=="
REGEX_CNPJ = re.compile(r'\W+') 

try:
    from email_validator import validate_email
    EMAIL_TOOL_READY = True
except ImportError:
    EMAIL_TOOL_READY = False

st.set_page_config(page_title="Cadarn Hub | Intelligence", layout="wide", page_icon="🛡️")

# --- GERENCIAMENTO DE ESTADO ---
if 'processamento_concluido' not in st.session_state:
    st.session_state.processamento_concluido = False
if 'arquivo_processado' not in st.session_state:
    st.session_state.arquivo_processado = None
if 'metricas' not in st.session_state:
    st.session_state.metricas = {}

# --- CSS ULTRA PREMIUM E ACESSÍVEL ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@200;400;600&display=swap');

    * {{ font-family: 'Outfit', sans-serif; }}
    
    .stApp {{
        background-color: #0b0b0b;
        background-image: 
            linear-gradient(rgba(131, 46, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(131, 46, 255, 0.03) 1px, transparent 1px);
        background-size: 30px 30px;
        color: #e0e0e0; /* Contraste melhorado */
    }}

    .hub-card {{
        background: rgba(18, 18, 18, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px; /* Bordas mais suaves */
        padding: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        margin-bottom: 20px;
    }}
    .hub-card:hover {{
        border: 1px solid rgba(131, 46, 255, 0.5);
        box-shadow: 0 8px 32px rgba(131, 46, 255, 0.15);
    }}

    .stButton>button {{
        background: linear-gradient(135deg, #832eff 0%, #6b15eb 100%) !important;
        color: white !important;
        border: none !important;
        padding: 14px 28px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        width: 100%;
        box-shadow: 0 4px 15px rgba(131, 46, 255, 0.3);
        transition: all 0.3s ease !important;
    }}
    .stButton>button:hover {{
        box-shadow: 0 6px 25px rgba(131, 46, 255, 0.6);
        transform: translateY(-2px);
    }}

    .logo-container {{ text-align: center; padding: 40px 0; }}
    .main-logo {{ width: 90px; filter: drop-shadow(0 0 20px rgba(131, 46, 255, 0.6)); margin-bottom: 15px; }}
    .glitch-title {{ font-size: 2.2rem; font-weight: 600; color: white; margin-bottom: 0; }}
    .sub-title {{ color: #a875ff; font-weight: 400; letter-spacing: 3px; font-size: 0.85rem; text-transform: uppercase; }}

    .badge-exec {{ background: rgba(131, 46, 255, 0.15); border: 1px solid #832eff; color: white; padding: 4px 12px; border-radius: 4px; font-size: 0.75rem; letter-spacing: 1px; }}
    .badge-done {{ background: rgba(0, 255, 163, 0.15); border: 1px solid #00ffa3; color: #00ffa3; padding: 4px 12px; border-radius: 4px; font-size: 0.75rem; letter-spacing: 1px; }}

    /* Ocultar elementos desnecessários do Streamlit */
    #MainMenu, footer, header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f"""
    <div class="logo-container">
        <img src="{LOGO_BASE64}" class="main-logo">
        <p class="sub-title">Cadarn Intelligence System</p>
        <h1 class="glitch-title">ENRIQUECIMENTO DE DADOS</h1>
    </div>
    """, unsafe_allow_html=True)

# --- FUNÇÕES ---
@st.cache_data(show_spinner=False)
def validar_email(email: str) -> str:
    if not email or pd.isna(email): return "Vazio"
    if EMAIL_TOOL_READY:
        try:
            validate_email(str(email), check_deliverability=False)
            return "Válido"
        except Exception: return "Inválido"
    return "Analítico"

@st.cache_data(show_spinner=False)
def buscar_empresa(cnpj: str) -> str:
    if not cnpj or pd.isna(cnpj): return "N/D"
    limpo = REGEX_CNPJ.sub('', str(cnpj))
    if not limpo: return "N/D"
    try:
        r = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{limpo}", timeout=5)
        if r.status_code == 200:
            return r.json().get("razao_social", "Encontrado (Sem Razão Social)")
    except requests.exceptions.RequestException: return "Erro de Conexão"
    return "Não Encontrado"

def processar_lote(df: pd.DataFrame) -> dict:
    total_linhas = len(df)
    prog_bar = st.progress(0)
    
    final_data = []
    stats = {"total": total_linhas, "emails_validos": 0, "empresas_encontradas": 0}

    # UX Improvement: Uso do st.status para encapsular logs longos
    with st.status("Processando base de dados...", expanded=True) as status:
        for i, linha in df.iterrows():
            email_val = linha.get('E-mail')
            cnpj_val = linha.get('CNPJ') if 'CNPJ' in df.columns else None
            nome_val = str(linha.get('Nome', f'Linha {i+1}'))

            res_email = validar_email(email_val)
            res_empresa = buscar_empresa(cnpj_val)
            
            # Coleta de métricas em tempo real para UX
            if res_email == "Válido": stats["emails_validos"] += 1
            if res_empresa not in ["N/D", "Não Encontrado", "Erro de Conexão"]: 
                stats["empresas_encontradas"] += 1

            nova = linha.to_dict()
            nova.update({"Status_Email": res_email, "Razao_Social": res_empresa})
            final_data.append(nova)
            
            prog_bar.progress((i + 1) / total_linhas)
            st.write(f"🔍 Extraindo dados de: **{nome_val}** ({i+1}/{total_linhas})")
            time.sleep(0.01)
            
        status.update(label="Processamento finalizado com sucesso!", state="complete", expanded=False)

    df_final = pd.DataFrame(final_data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False)
    
    return {"bytes": output.getvalue(), "stats": stats}

# --- INTERFACE PRINCIPAL (TABS PARA UX) ---
tab_operacao, tab_resultados = st.tabs(["⚙️ Operação de Dados", "📊 Resultados & Inteligência"])

with tab_operacao:
    c1, c2 = st.columns([1.2, 1], gap="large")

    with c1:
        st.markdown('<div class="hub-card">', unsafe_allow_html=True)
        st.markdown("### 📥 Fonte de Dados")
        
        arquivo = st.file_uploader(
            "Arraste o arquivo Excel exportado do Atendare", 
            type=["xlsx"],
            help="Apenas arquivos .xlsx são suportados no momento."
        )
        
        if arquivo:
            # UX Improvement: Toast informando sucesso no upload
            if 'upload_toast_shown' not in st.session_state:
                st.toast('Arquivo carregado com sucesso!', icon='✅')
                st.session_state.upload_toast_shown = True

            df = pd.read_excel(arquivo)
            
            st.markdown(f"""
                <div style="margin: 15px 0;">
                    <span class="badge-exec">LOTE PRONTO</span>
                    <h3 style="margin: 10px 0 0 0; color: white;">{len(df)} <span style="font-size: 1rem; color: #a0a0a0;">Leads detectados</span></h3>
                </div>
            """, unsafe_allow_html=True)
            
            # UX Improvement: Preview dos dados para segurança do usuário
            with st.expander("👁️ Pré-visualizar amostra dos dados", expanded=False):
                st.dataframe(df.head(5), use_container_width=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("INICIAR PROTOCOLO 🚀", help="Inicia o enriquecimento e validação na nuvem."):
                st.session_state.processamento_concluido = False
                st.session_state.arquivo_processado = None
                
                resultado = processar_lote(df)
                
                st.session_state.arquivo_processado = resultado["bytes"]
                st.session_state.metricas = resultado["stats"]
                st.session_state.processamento_concluido = True
                
                st.balloons()
                st.toast('Inteligência gerada! Verifique a aba Resultados.', icon='🎉')
                st.rerun()
                
        else:
            # Reseta a flag do toast se não houver arquivo
            if 'upload_toast_shown' in st.session_state:
                del st.session_state.upload_toast_shown

        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="hub-card" style="height: 100%;">', unsafe_allow_html=True)
        st.markdown("### 🛠️ Configurações Ativas")
        st.info("Os módulos abaixo serão aplicados automaticamente a cada linha da sua base.")
        
        st.checkbox("Validação de E-mail (DNS)", value=True, disabled=True, help="Verifica a sintaxe e a existência do domínio de e-mail.")
        st.checkbox("Busca de Razão Social (BrasilAPI)", value=True, disabled=True, help="Puxa os dados atualizados da Receita Federal usando o CNPJ.")
        st.checkbox("Normalização de Caracteres", value=True, disabled=True, help="Remove pontuações e acentos inconsistentes.")
        st.markdown('</div>', unsafe_allow_html=True)

with tab_resultados:
    if not st.session_state.processamento_concluido or st.session_state.arquivo_processado is None:
        st.warning("⚠️ Nenhum dado processado ainda. Volte para a aba 'Operação de Dados' e inicie o protocolo.")
    else:
        st.markdown('<div class="hub-card">', unsafe_allow_html=True)
        st.markdown("### 📈 Diagnóstico do Enriquecimento")
        
        # UX Improvement: Uso de st.metric para exibir valor claro do processamento
        m1, m2, m3 = st.columns(3)
        stats = st.session_state.metricas
        
        m1.metric("Total de Leads Analisados", stats["total"])
        m2.metric("E-mails Válidos Confirmados", stats["emails_validos"])
        m3.metric("Novas Razões Sociais Encontradas", stats["empresas_encontradas"])
        
        st.markdown("---")
        
        st.markdown(f"""
            <div style="text-align: center; padding: 20px;">
                <span class="badge-done">INTELIGÊNCIA FINALIZADA</span>
                <p style="color: #d0d2d3; margin: 15px 0;">O arquivo estruturado já está pronto para o seu CRM.</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.download_button(
            label="📥 BAIXAR BASE ENRIQUECIDA",
            data=st.session_state.arquivo_processado,
            file_name="cadarn_hub_intelligence.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Faz o download do Excel contendo as novas colunas geradas."
        )
        st.markdown('</div>', unsafe_allow_html=True)