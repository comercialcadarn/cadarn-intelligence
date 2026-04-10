import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Cadarn Hub | Intelligence", layout="wide", page_icon="🛡️")

# --- CSS COMPACTO (FIX DE ESPAÇO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@200;400;600&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background-color: #0b0b0b; color: #d0d2d3; }
    .logo-container { text-align: center; padding: 5px 0; margin-top: -50px; } /* Subiu mais ainda */
    .glitch-title { font-size: 1.5rem; color: white; letter-spacing: 2px; }
    .hub-card {
        background: rgba(25, 25, 25, 0.9);
        border: 1px solid rgba(131, 46, 255, 0.2);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .badge-discovery { background: #832eff; color: white; padding: 2px 8px; border-radius: 5px; font-size: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- INTELIGÊNCIA DE DESCOBERTA ---

def extrair_dominio(email):
    if pd.isna(email) or "@" not in str(email): return None
    dominios_comuns = ['gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com', 'icloud.com']
    dominio = str(email).split('@')[-1].lower()
    return dominio if dominio not in dominios_comuns else None

def buscar_por_nome(nome_empresa):
    """Busca aproximada quando não há CNPJ"""
    if pd.isna(nome_empresa) or len(str(nome_empresa)) < 3: return "Inconclusivo"
    # Aqui poderíamos integrar com a API da Receita que permite busca por QSA ou Nome
    # Por enquanto, simulamos a busca de Razão Social
    return f"🔍 Verificar: {str(nome_empresa).upper()}"

@st.cache_data(ttl=3600)
def protocolo_enriquecimento(row):
    cnpj = re.sub(r'\D', '', str(row.get('CNPJ', '')))
    email = row.get('E-mail', '')
    nome = row.get('Nome', '')
    
    # 1. Prioridade Máxima: CNPJ
    if len(cnpj) == 14:
        try:
            r = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}", timeout=4)
            if r.status_code == 200:
                data = r.json()
                return data.get("razao_social"), "VIA CNPJ", data.get("municipio")
        except: pass

    # 2. Segunda Via: Domínio Corporativo
    dominio = extrair_dominio(email)
    if dominio:
        return f"Empresa de {dominio}", "VIA DOMÍNIO", "Localizar via Site"

    # 3. Terceira Via: Nome/Razão
    if pd.notna(nome):
        return buscar_por_nome(nome), "VIA NOME", "N/D"

    return "Não Identificado", "FALHA", "N/D"

# --- INTERFACE ---
st.markdown('<div class="logo-container"><h1 class="glitch-title">CADARN HUB <span style="color:#832eff">INTEL</span></h1></div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns([1.5, 1, 1])

with c1:
    st.markdown('<div class="hub-card">', unsafe_allow_html=True)
    arquivo = st.file_uploader("Upload Base Atendare", type=["xlsx"])
    st.markdown('</div>', unsafe_allow_html=True)

if arquivo:
    df = pd.read_excel(arquivo)
    
    with c2:
        st.markdown('<div class="hub-card">', unsafe_allow_html=True)
        st.write("📈 **Potencial de Recuperação**")
        leads_sem_cnpj = df['CNPJ'].isna().sum() if 'CNPJ' in df.columns else len(df)
        st.write(f"Leads sem CNPJ: **{leads_sem_cnpj}**")
        st.caption("O sistema tentará identificar via e-mail/nome.")
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="hub-card">', unsafe_allow_html=True)
        st.write("⚙️ **Ações Disponíveis**")
        btn = st.button("EXECUTAR PROTOCOLO 🚀", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if btn:
        resultados = []
        barra = st.progress(0)
        
        for i, row in df.iterrows():
            razao, metodo, local = protocolo_enriquecimento(row)
            
            nova_linha = row.to_dict()
            nova_linha['Razão Social (Enriquecida)'] = razao
            nova_linha['Método de Descoberta'] = metodo
            nova_linha['Cidade Detectada'] = local
            resultados.append(nova_linha)
            barra.progress((i+1)/len(df))

        df_final = pd.DataFrame(resultados)
        
        st.markdown("---")
        st.subheader("📋 Visualização dos Dados Inteligentes")
        st.dataframe(df_final[['Nome', 'E-mail', 'CNPJ', 'Razão Social (Enriquecida)', 'Método de Descoberta']].head(10))
        
        output = BytesIO()
        df_final.to_excel(output, index=False)
        st.download_button("📥 BAIXAR PLANILHA COMPLETA", output.getvalue(), "base_enriquecida_cadarn.xlsx", use_container_width=True)