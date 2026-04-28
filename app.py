import streamlit as st
import pandas as pd
import time
import re
import asyncio
import aiohttp
from datetime import datetime
from io import BytesIO

# --- VALIDAÇÃO DE DEPENDÊNCIAS CRÍTICAS ---
try:
    import openpyxl
    import xlsxwriter
except ImportError:
    st.error("🚨 **Falha Crítica de Dependência!**")
    st.warning("Os pacotes `openpyxl` e `xlsxwriter` são obrigatórios para manipulação de planilhas.")
    st.info("💻 **Como resolver:** Pare o terminal e rode: `python -m pip install openpyxl xlsxwriter`")
    st.stop()

try:
    import dns.resolver
    DNS_READY = True
except ImportError:
    DNS_READY = False

st.set_page_config(page_title="Cadarn Hub | Intelligence", layout="wide", page_icon="🛡️")

# --- IMPORTS DE UI (ARQUITETURA MODULAR) ---
# Importamos a estética separada para manter este arquivo focado no motor de dados
from ui_components import renderizar_css_e_particulas, renderizar_cabecalho, render_stepper

# --- CONFIGURAÇÕES E CONSTANTES ---
DOMINIOS_GENERICOS = {'gmail.com', 'hotmail.com', 'yahoo.com', 'yahoo.com.br', 'outlook.com', 'icloud.com', 'uol.com.br', 'bol.com.br', 'terra.com.br', 'ig.com.br'}

# --- NOME DAS ABAS ---
aba_op, aba_res, aba_hist = "⚙️ Operação", "📊 Resultados", "📚 Histórico"
abas = [aba_op, aba_res, aba_hist]

# --- GERENCIAMENTO DE ESTADO ---
def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

init_state('current_tab', aba_op) 
init_state('processamento_concluido', False)
init_state('arquivo_processado_xlsx', None)
init_state('arquivo_processado_csv', None)
init_state('relatorio_auditoria', "")
init_state('metricas', {})
init_state('merge_stats', {}) 
init_state('historico', []) 
init_state('status_sessao', 1)
init_state('tema_escuro', True)
if 'cache_mx' not in st.session_state: 
    st.session_state.cache_mx = {}

def hard_reset():
    chaves_para_limpar = ['processamento_concluido', 'arquivo_processado_xlsx', 'arquivo_processado_csv', 'relatorio_auditoria', 'metricas', 'merge_stats', 'cache_mx']
    for chave in chaves_para_limpar:
        if chave in st.session_state:
            del st.session_state[chave]
    st.session_state.current_tab = aba_op
    st.session_state.status_sessao = 1
    st.rerun()

# --- CONTROLE DE NAVEGAÇÃO ---
def sync_tabs():
    st.session_state.current_tab = st.session_state.nav_radio_key

if st.session_state.current_tab not in abas:
    st.session_state.current_tab = aba_op

idx_aba = abas.index(st.session_state.current_tab)

# INJEÇÃO DO FRONTEND (CSS, JS e Cabeçalho)
renderizar_css_e_particulas()

tab_idx = abas.index(st.session_state.current_tab)
pills_html = '<div class="nav-pill-bar">'
for i, aba in enumerate(abas):
    ativo = "active" if i == tab_idx else ""
    pills_html += f'<div class="nav-pill {ativo}" onclick="void(0)">{aba}</div>'
pills_html += '</div>'
st.markdown(pills_html, unsafe_allow_html=True)
st.radio("Nav", abas, horizontal=True, index=idx_aba, key="nav_radio_key", on_change=sync_tabs, label_visibility="collapsed")

renderizar_cabecalho()

# --- NÚCLEO DE INTELIGÊNCIA ---
def categorizar_email(email: str) -> str:
    dominio = extrair_dominio_de_email(email)
    if not dominio: return "N/D"
    if any(g in email.lower() for g in DOMINIOS_GENERICOS):
        return "Genérico (Pessoal)"
    return "Corporativo (B2B)"

def validar_email_profundo(email: str) -> str:
    if pd.isna(email) or not isinstance(email, str) or email.strip() == "": return "Vazio"
    email_str = email.strip().lower()
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email_str): return "Inválido (Sintaxe)"
        
    dominio = email_str.split('@')[1]
    if dominio in st.session_state.cache_mx:
        return "Válido (Sintaxe + MX)" if st.session_state.cache_mx[dominio] else "Inválido (Domínio Morto)"
        
    try:
        if DNS_READY: dns.resolver.resolve(dominio, 'MX')
        st.session_state.cache_mx[dominio] = True
        return "Válido (Sintaxe + MX)"
    except Exception:
        st.session_state.cache_mx[dominio] = False
        return "Inválido (Domínio Morto)"

async def fetch_cnpj_async(cnpj: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> dict:
    limpo = re.sub(r'\D', '', str(cnpj)).zfill(14)
    default = {"cnpj": cnpj, "razao_social": "N/D", "cnae": "N/D", "atividade": "N/D"}
    if len(limpo) != 14: return default

    url = f"https://brasilapi.com.br/api/cnpj/v1/{limpo}"
    async with semaphore:
        for attempt in range(3):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=7)) as r:
                    if r.status == 200:
                        data = await r.json()
                        return {
                            "cnpj": cnpj,
                            "razao_social": data.get("razao_social", "Encontrado"),
                            "cnae": str(data.get("cnae_fiscal", "N/D")),
                            "atividade": data.get("cnae_fiscal_descricao", "N/D")
                        }
                    elif r.status == 429:
                        await asyncio.sleep(1.5 ** attempt) 
                        continue
                    else: break
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt == 2: default["atividade"] = "API Indisponível/Timeout"
                await asyncio.sleep(1)
        return default

def normalizar_nomes(nome):
    if pd.isna(nome) or not isinstance(nome, str): return ""
    excecoes = ['de', 'da', 'do', 'das', 'dos', 'e']
    palavras = nome.strip().lower().split()
    return " ".join([p.capitalize() if p not in excecoes else p for p in palavras])

def sanitizar_csv(val):
    if isinstance(val, str) and val.startswith(('=', '+', '-', '@')): return f"'{val}"
    return val

def formatar_telefone_vetorizado(s: pd.Series) -> pd.Series:
    def formatar(num_str):
        limpo = re.sub(r'\D', '', str(num_str).split('.')[0])
        if len(limpo) == 11: return f"({limpo[:2]}) {limpo[2:7]}-{limpo[7:]}"
        elif len(limpo) == 10: return f"({limpo[:2]}) {limpo[2:6]}-{limpo[6:]}"
        return num_str
    return s.apply(lambda x: ", ".join([formatar(n) for n in str(x).split(',')]) if pd.notna(x) else "")

def extrair_dominio_de_email(email):
    if not isinstance(email, str) or '@' not in email: return ""
    try: return email.split('@')[1].split('.')[0].strip().lower()
    except: return ""

def formatar_cnpj_mascara(cnpj_str):
    if pd.isna(cnpj_str): return ""
    limpo = re.sub(r'\D', '', str(cnpj_str)).zfill(14)
    if len(limpo) == 14:
        return f"{limpo[:2]}.{limpo[2:5]}.{limpo[5:8]}/{limpo[8:12]}-{limpo[12:]}"
    return cnpj_str

def adivinhar_inteligente(df_temp, categoria):
    sinonimos = {
        "id": ["id", "identificador", "codigo", "código", "pk", "uuid"],
        "empresa": ["empresa", "razao", "razão", "fantasia", "company", "cliente", "conta"],
        "email": ["email", "e-mail", "correio"],
        "nome": ["nome", "contato", "cliente", "responsavel", "responsável"],
        "tele": ["tele", "celular", "whatsapp", "wpp", "fone", "mobile"],
        "cnpj": ["cnpj", "documento", "doc"]
    }
    cols_lower = [c.lower() for c in df_temp.columns]
    for termo in sinonimos.get(categoria, [categoria]):
        for i, col in enumerate(cols_lower):
            if termo in col:
                return df_temp.columns[i]
    return df_temp.columns[0] if len(df_temp.columns) > 0 else ""

# --- MOTOR DE EXECUÇÃO (PIPELINE) ---
def executar_pipeline_elite(df_base, col_id, col_nome, col_empresa, col_cnpj, col_email, col_tel, config):
    st.session_state.status_sessao = 3
    df = df_base.copy()
    
    duplicadas_removidas = 0
    if config.get('desduplicar', False):
        tamanho_original = len(df)
        subset_drop = [col for col in [col_email, col_cnpj] if col in df.columns]
        if subset_drop:
            df = df.drop_duplicates(subset=subset_drop)
            duplicadas_removidas = tamanho_original - len(df)

    stats = {"total": len(df), "emails_validos": 0, "empresas_encontradas": 0}
    start_time = time.time()
    
    with st.status("🚀 Iniciando Motor de Inteligência...", expanded=True) as status_container:
        log_ph = st.empty()
        
        log_ph.markdown("🔄 **Etapa 1:** Normalizando dados em memória...")
        if config['norm_nomes'] and col_nome in df.columns:
            df[col_nome] = df[col_nome].apply(normalizar_nomes)
        if config['padronizar_tel'] and col_tel in df.columns:
            df[col_tel] = formatar_telefone_vetorizado(df[col_tel])

        df["Status de Email (Validação)"] = "N/D"
        df["Tipo de E-mail"] = "N/D"
        
        if config['validar_email'] and col_email in df.columns:
            log_ph.markdown("🔄 **Etapa 2:** Validando integridade e tipo de E-mails (DNS/MX)...")
            df["Status de Email (Validação)"] = df[col_email].apply(validar_email_profundo)
            df["Tipo de E-mail"] = df[col_email].apply(categorizar_email)
            stats["emails_validos"] = len(df[df["Status de Email (Validação)"].str.contains("Válido", na=False)])

        df["Descrição da Atividade da Empresa"] = "N/D"
        df["CNAE da Empresa"] = "N/D"
        
        if config['buscar_cnpj'] and col_cnpj in df.columns:
            cnpjs_unicos = df[col_cnpj].dropna().unique()
            prog_bar = st.progress(0)
            
            async def processar_lotes():
                sem = asyncio.Semaphore(15) 
                resultados = {}
                async with aiohttp.ClientSession() as session:
                    chunk_size = 50
                    for i in range(0, len(cnpjs_unicos), chunk_size):
                        lote = cnpjs_unicos[i:i+chunk_size]
                        tasks = [fetch_cnpj_async(cnpj, session, sem) for cnpj in lote]
                        resps = await asyncio.gather(*tasks)
                        for r in resps: resultados[r['cnpj']] = r
                        
                        processados = min(i + chunk_size, len(cnpjs_unicos))
                        prog = processados / len(cnpjs_unicos) if len(cnpjs_unicos) > 0 else 1.0
                        prog_bar.progress(prog)
                        
                        log_ph.markdown(f"🔄 **Etapa 3:** Consultando APIs externas em Lote ({processados}/{len(cnpjs_unicos)} CNPJs)...")
                return resultados

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            mapa_cnpjs = loop.run_until_complete(processar_lotes())
            prog_bar.empty() 
            
            df['__api_data'] = df[col_cnpj].map(mapa_cnpjs)
            df["Descrição da Atividade da Empresa"] = df['__api_data'].apply(lambda x: x['atividade'] if isinstance(x, dict) else "N/D")
            df["CNAE da Empresa"] = df['__api_data'].apply(lambda x: x['cnae'] if isinstance(x, dict) else "N/D")
            
            if col_empresa in df.columns:
                df[col_empresa] = df.apply(lambda row: row['__api_data']['razao_social'] if isinstance(row.get('__api_data'), dict) and row['__api_data']['razao_social'] != "N/D" else row[col_empresa], axis=1)
            
            df.drop(columns=['__api_data'], inplace=True)
            stats["empresas_encontradas"] = len(df[df["CNAE da Empresa"] != "N/D"])

        log_ph.markdown("✅ **Montando matriz estrita de exportação...**")
        status_container.update(label="Processamento Finalizado com Sucesso!", state="complete", expanded=False)
    
    colunas_saida = [
        ("ID", col_id), ("Nome", col_nome), ("Empresa", col_empresa), ("Cargo", "Cargo"), 
        ("Telefone", col_tel), ("Email", col_email), ("Tipo de E-mail (Categoria)", "Tipo de E-mail"),
        ("CNPJ da Empresa", col_cnpj), ("Descrição da Atividade da Empresa", "Descrição da Atividade da Empresa"),
        ("CNAE da Empresa", "CNAE da Empresa"), ("Status de Email (Validação)", "Status de Email (Validação)")
    ]
    
    df_out = pd.DataFrame()
    for col_saida, col_origem in colunas_saida:
        if col_origem in df.columns:
            if col_saida == "CNPJ da Empresa":
                df_out[col_saida] = df[col_origem].apply(formatar_cnpj_mascara)
            elif col_saida == "Email":
                df_out[col_saida] = df[col_origem].astype(str).str.lower().apply(sanitizar_csv)
            else:
                df_out[col_saida] = df[col_origem].apply(sanitizar_csv)
        else:
            df_out[col_saida] = "" 

    output_xlsx = BytesIO()
    with pd.ExcelWriter(output_xlsx, engine='xlsxwriter') as writer: 
        df_out.to_excel(writer, index=False)
    csv_bytes = df_out.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8')
    
    tempo_total = time.time() - start_time
    merge_info = st.session_state.merge_stats
    timestamp_formatado = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    timestamp_arquivo = datetime.now().strftime("%d%m%Y_%H%M")
    
    auditoria_txt = f"""=== CADARN HUB | RELATÓRIO DE AUDITORIA ===
Data do Job: {timestamp_formatado}
Tempo de Execução CPU: {tempo_total:.2f} segundos

[1] ENTRADA DE DADOS E CRUZAMENTO
- Leads originais carregados: {merge_info.get('total_linhas_iniciais', 0)}
- Leads descartados por falta de chaves: {merge_info.get('descartados', 0)}
- Duplicatas removidas no pré-job: {duplicadas_removidas}

[2] PROCESSAMENTO E HIGIENIZAÇÃO
- Leads únicos processados: {stats['total']}
- E-mails Válidos (Sintaxe + DNS): {stats['emails_validos']}
- Empresas encontradas via Integração de API: {stats['empresas_encontradas']}

Status Final: SUCESSO. Base higienizada e formatada.
==============================================="""
    
    registro_historico = {
        "timestamp_str": timestamp_formatado,
        "arquivo_sufixo": timestamp_arquivo,
        "leads": stats['total'],
        "health": int(((stats["emails_validos"] + stats["empresas_encontradas"]) / (stats["total"] * 2)) * 100) if stats["total"] > 0 else 0,
        "xlsx_data": output_xlsx.getvalue(),
        "csv_data": csv_bytes,
        "auditoria_data": auditoria_txt.encode('utf-8')
    }
    
    st.session_state.arquivo_processado_xlsx = registro_historico["xlsx_data"]
    st.session_state.arquivo_processado_csv = registro_historico["csv_data"]
    st.session_state.relatorio_auditoria = registro_historico["auditoria_data"]
    stats["tipos_email"] = df["Tipo de E-mail"].value_counts().to_dict()
    st.session_state.metricas = stats
    st.session_state.processamento_concluido = True
    st.session_state.status_sessao = 4 
    
    st.session_state.historico.insert(0, registro_historico)
    st.session_state.historico = st.session_state.historico[:5]
    
    st.balloons()
    st.session_state.current_tab = aba_res 
    st.rerun()

# --- INTERFACE PRINCIPAL ---
if st.session_state.current_tab == aba_op:
    c1, c2 = st.columns([1.2, 1], gap="large")
    
    with c1:
        ph_stepper = st.empty()
        
        with st.container(border=True):
            st.markdown("### 📥 Ingestão de Dados")
            f_contatos = st.file_uploader("1. Base de Contatos (.xlsx)", type=["xlsx"])
            f_empresas = st.file_uploader("2. Base de Empresas (.xlsx)", type=["xlsx"])
            
            is_ready = f_contatos and f_empresas
            st.session_state.status_sessao = 2 if is_ready else 1

        with ph_stepper.container():
            with st.container(border=True):
                st.markdown("<p style='font-size: 0.9rem; font-weight: 600;'>🔄 Status do Job</p>", unsafe_allow_html=True)
                render_stepper(st.session_state.status_sessao)

        if is_ready:
            with st.spinner("Estruturando planilhas em memória..."):
                df_c = pd.read_excel(f_contatos)
                df_e = pd.read_excel(f_empresas)
            
            c_inf1, c_inf2 = st.columns(2)
            c_inf1.markdown(f"<div class='file-meta'>📁 Contatos: {len(df_c)} lin | {len(df_c.columns)} col</div>", unsafe_allow_html=True)
            c_inf2.markdown(f"<div class='file-meta'>📁 Empresas: {len(df_e)} lin | {len(df_e.columns)} col</div>", unsafe_allow_html=True)
            
            st.markdown("### 🔗 Mapeamento Dinâmico e Resgate")
            st.caption("Se a empresa estiver vazia, extrairemos o domínio do E-mail de resgate automaticamente.")
            
            m1, m2, m3 = st.columns(3)
            chave_c = m1.selectbox("Empresa (Contatos)", df_c.columns, index=list(df_c.columns).index(adivinhar_inteligente(df_c, "empresa")))
            chave_email = m2.selectbox("E-mail (Resgate)", df_c.columns, index=list(df_c.columns).index(adivinhar_inteligente(df_c, "email")))
            chave_e = m3.selectbox("Empresa (Base CNPJ)", df_e.columns, index=list(df_e.columns).index(adivinhar_inteligente(df_e, "empresa")))
            
            lixos_regex = r'^(nan|null|none|)$'
            mask_sem_empresa = df_c[chave_c].astype(str).str.strip().str.lower().str.match(lixos_regex) | df_c[chave_c].isna()
            mask_sem_email = df_c[chave_email].astype(str).str.strip().str.lower().str.match(lixos_regex) | df_c[chave_email].isna()
            
            linhas_iniciais = len(df_c)
            
            df_descartados = df_c[mask_sem_empresa & mask_sem_email].copy()
            df_c = df_c[~(mask_sem_empresa & mask_sem_email)].copy()
            linhas_descartadas = len(df_descartados)
            
            mask_sem_empresa = df_c[chave_c].astype(str).str.strip().str.lower().str.match(lixos_regex) | df_c[chave_c].isna()
            df_c.loc[mask_sem_empresa, chave_c] = df_c.loc[mask_sem_empresa, chave_email].apply(extrair_dominio_de_email)
            
            df_c['_key'] = df_c[chave_c].astype(str).str.strip().str.lower()
            df_c = df_c[~df_c['_key'].str.match(lixos_regex)]
            
            df_e['_key'] = df_e[chave_e].astype(str).str.strip().str.lower()
            df_e = df_e[~df_e['_key'].str.match(lixos_regex)]
            df_e = df_e.drop_duplicates(subset=['_key'])
            
            df_merged = pd.merge(df_c, df_e, on='_key', how='inner').drop(columns=['_key'])
            
            st.session_state.merge_stats = {"total_linhas_iniciais": linhas_iniciais, "cruzados": len(df_merged), "descartados": linhas_descartadas}
            
            if linhas_descartadas > 0:
                st.warning(f"⚠️ **{linhas_descartadas} leads foram descartados** pois não continham Empresa nem E-mail válido para resgate.")
                csv_descartados = df_descartados.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8')
                st.download_button("🗑️ Baixar Leads Descartados (.CSV)", data=csv_descartados, file_name="leads_rejeitados_por_falta_de_chaves.csv", mime="text/csv")

            if len(df_merged) > 0:
                st.toast("Cruzamento de dados concluído com sucesso!", icon="🤝")
                with st.expander("👀 Preview dos Dados Cruzados", expanded=False):
                    df_preview = df_merged.head(5)
                    st.dataframe(df_preview.style.highlight_null(color='rgba(255, 75, 75, 0.2)'), use_container_width=True, hide_index=True)
            else:
                st.error("⚠️ As chaves selecionadas não geraram nenhuma correspondência.")

    with c2:
        with st.container(border=True):
            st.markdown("### 🛠️ Parametrização Final")
            
            config = {}
            with st.expander("⚙️ Configurações Avançadas", expanded=False):
                config["desduplicar"] = st.checkbox("🧹 Remover leads duplicados", True, help="Remove leads que possuem o mesmo E-mail ou CNPJ, mantendo apenas a primeira ocorrência.")
                config["norm_nomes"] = st.checkbox("Aa Normalizar Nomes Próprios", True, help="Formata nomes despadronizados. Ex: 'JOAO DA SILVA' vira 'Joao da Silva'.")
                config["padronizar_tel"] = st.checkbox("📞 Padronizar Telefones", True, help="Aplica formatação universal de DDI/DDD (XX) XXXXX-XXXX aos números.")
                config["validar_email"] = st.checkbox("📧 Validação MX de E-mails", True, help="Faz um ping no servidor DNS para verificar se a caixa de e-mail está ativa ou morta.")
                config["buscar_cnpj"] = st.checkbox("🏢 Enriquecimento BrasilAPI", True, help="Usa o CNPJ para buscar a Razão Social real e a Descrição da Atividade (CNAE) da empresa em tempo real.")
            
            if is_ready and len(df_merged) > 0:
                st.markdown("#### Identificação de Colunas de Saída")
                todas_cols = ['Nenhuma'] + list(df_merged.columns)

                def safe_index(col_guess):
                    return todas_cols.index(col_guess) if col_guess in todas_cols else 0

                col_id = st.selectbox("Coluna de ID", todas_cols, index=safe_index(adivinhar_inteligente(df_merged, "id")))
                col_nome = st.selectbox("Coluna de Nome", todas_cols, index=safe_index(adivinhar_inteligente(df_merged, "nome")))
                col_empresa = st.selectbox("Coluna de Empresa Final", todas_cols, index=safe_index(adivinhar_inteligente(df_merged, "empresa")))
                col_email = st.selectbox("Coluna de Email", todas_cols, index=safe_index(adivinhar_inteligente(df_merged, "email")))
                col_tel = st.selectbox("Coluna de Telefone", todas_cols, index=safe_index(adivinhar_inteligente(df_merged, "tele")))
                col_cnpj = st.selectbox("Coluna de CNPJ", todas_cols, index=safe_index(adivinhar_inteligente(df_merged, "cnpj")))

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("INICIAR MOTOR DE INTELIGÊNCIA 🚀", type="primary"):
                    st.session_state.processamento_concluido = False
                    executar_pipeline_elite(df_merged, col_id, col_nome, col_empresa, col_cnpj, col_email, col_tel, config)
            
            st.markdown("<hr style='margin: 10px 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
            st.button("🗑️ Nova Operação (Limpar Memória)", on_click=hard_reset, use_container_width=True)
            st.markdown("<script>const btns = window.parent.document.querySelectorAll('.stButton button'); btns[btns.length-1].classList.add('btn-reset');</script>", unsafe_allow_html=True)

elif st.session_state.current_tab == aba_res:
    if not st.session_state.processamento_concluido:
        st.warning("Nenhum dado processado ainda. Volte para a aba de operação para iniciar.")
        st.button("← VOLTAR", on_click=lambda: st.session_state.update(current_tab=aba_op))
    else:
        with st.container(border=True):
            st.markdown("### 📈 Diagnóstico de Inteligência (Último Job)")
            stats = st.session_state.metricas
            merge_stats = st.session_state.merge_stats
            
            linhas_originais = merge_stats.get("total_linhas_iniciais", stats["total"])
            delta_leads = stats["total"] - linhas_originais
            
            m1, m2, m3 = st.columns(3)
            for col, icone, label, valor, cor in [
                (m1, "👥", "Leads Únicos", stats["total"], "#832eff"),
                (m2, "📧", "E-mails Válidos MX", stats["emails_validos"], "#00ffa3"),
                (m3, "🏢", "Empresas via API", stats["empresas_encontradas"], "#f9c74f"),
            ]:
                col.markdown(f"""
                <div style="background: linear-gradient(135deg, rgba(131,46,255,0.08), rgba(0,0,0,0));
                    border: 1px solid rgba(131,46,255,0.2); border-radius:14px; padding:20px 18px; text-align:center;">
                  <div style="font-size:1.8rem;">{icone}</div>
                  <div style="font-size:2.2rem; font-weight:700; color:{cor}; margin:6px 0;">{valor:,}</div>
                  <div style="font-size:0.78rem; color:var(--text-muted); text-transform:uppercase;
                      letter-spacing:1.5px; font-weight:600;">{label}</div>
                </div>
                """, unsafe_allow_html=True)
            
            health_score = int(((stats["emails_validos"] + stats["empresas_encontradas"]) / (stats["total"] * 2)) * 100) if stats["total"] > 0 else 0
            cor_gauge = "#00ffa3" if health_score >= 75 else "#f9c74f" if health_score >= 40 else "#ff4b4b"
            circunferencia = 251.2  
            progresso_arco = circunferencia * (1 - health_score / 100)
            
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:24px; margin: 16px 0;">
              <svg width="110" height="110" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="10"/>
                <circle cx="50" cy="50" r="40" fill="none" stroke="{cor_gauge}" stroke-width="10"
                  stroke-dasharray="{circunferencia}" stroke-dashoffset="{progresso_arco:.1f}"
                  stroke-linecap="round" transform="rotate(-90 50 50)"
                  style="transition: stroke-dashoffset 1s ease; filter: drop-shadow(0 0 6px {cor_gauge});"/>
                <text x="50" y="55" text-anchor="middle" font-size="18" font-weight="700"
                  fill="{cor_gauge}" font-family="Outfit, sans-serif">{health_score}%</text>
              </svg>
              <div>
                <div style="font-size:1.1rem; font-weight:700; color:var(--text-main);">Data Health Score</div>
                <div style="font-size:0.85rem; color:var(--text-muted); margin-top:4px;">Índice de qualidade da base processada</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.success("Formato de saída gerado. Arquivos restritos disponíveis abaixo.")
            
            tipos = stats.get("tipos_email", {})
            if tipos:
                st.markdown("<h4 style='color: var(--title-color); margin-top: 15px;'>🎯 Perfil da Base Final</h4>", unsafe_allow_html=True)
                cols_t = st.columns(len(tipos))
                for idx, (tipo, qtde) in enumerate(tipos.items()):
                    cols_t[idx].markdown(f"""
                    <div style="background: rgba(131,46,255,0.05); border-left: 4px solid #832eff; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 1px;">{tipo}</div>
                        <div style="font-size: 1.6rem; font-weight: 700; color: var(--text-main);">{qtde} <span style="font-size: 0.8rem; font-weight: 400; color: var(--text-muted);">leads</span></div>
                    </div>
                    """, unsafe_allow_html=True)
            
            timestamp_arquivo = datetime.now().strftime("%d%m%Y_%H%M")
            
            d1, d2, d3 = st.columns(3)
            with d1:
                st.download_button("📥 BAIXAR .XLSX", data=st.session_state.arquivo_processado_xlsx, file_name=f"cadarn_base_{timestamp_arquivo}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            with d2:
                st.download_button("📥 BAIXAR .CSV", data=st.session_state.arquivo_processado_csv, file_name=f"cadarn_base_{timestamp_arquivo}.csv", mime="text/csv", use_container_width=True)
            with d3:
                st.download_button("📋 LOG DE AUDITORIA", data=st.session_state.relatorio_auditoria, file_name=f"auditoria_{timestamp_arquivo}.txt", mime="text/plain", use_container_width=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("🔄 VOLTAR E PROCESSAR NOVA BASE", on_click=hard_reset)

elif st.session_state.current_tab == aba_hist:
    with st.container(border=True):
        st.markdown("### 📚 Histórico de Sessões Recentes")
        if not st.session_state.historico:
            st.markdown("""
            <div style="text-align: center; padding: 50px 20px; opacity: 0.7;">
                <div style="font-size: 3.5rem; margin-bottom: 15px;">📭</div>
                <h3 style="color: var(--text-main); font-weight: 600;">Nenhum Job Realizado</h3>
                <p style="color: var(--text-muted); font-size: 0.95rem;">Suas bases processadas, métricas e logs de auditoria<br>aparecerão aqui para download rápido durante sua sessão.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for i, reg in enumerate(st.session_state.historico):
                cor_health = "#00ffa3" if reg['health'] >= 75 else "#f9c74f" if reg['health'] >= 40 else "#ff4b4b"
                
                st.markdown(f"""
                <div class="history-card">
                  <div style="display:flex; gap:16px; margin-bottom:8px; align-items:flex-start;">
                    <div style="display:flex; flex-direction:column; align-items:center;">
                      <div style="width:14px; height:14px; border-radius:50%; background:{cor_health};
                          box-shadow:0 0 8px {cor_health}; margin-top:4px; flex-shrink:0;"></div>
                      <div style="width:2px; background:rgba(131,46,255,0.2); flex:1; min-height:40px;"></div>
                    </div>
                    <div style="background:rgba(131,46,255,0.05); border:1px solid rgba(131,46,255,0.15);
                        border-radius:12px; padding:14px 18px; flex:1;">
                      <div style="font-size:0.75rem; color:var(--text-muted); font-weight:600;
                          text-transform:uppercase; letter-spacing:1px;">Job #{i+1}</div>
                      <div style="font-size:1rem; font-weight:700; color:var(--text-main); margin:4px 0;">
                          {reg['timestamp_str']}</div>
                      <div style="display:flex; gap:20px; font-size:0.85rem; color:var(--text-muted);">
                        <span>📇 <strong style="color:var(--text-main);">{reg['leads']}</strong> leads</span>
                        <span>❤️ Health: <strong style="color:{cor_health};">{reg['health']}%</strong></span>
                      </div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
                
                hd1, hd2, hd3 = st.columns(3)
                with hd1:
                    st.download_button("📥 BAIXAR .XLSX", data=reg["xlsx_data"], file_name=f"cadarn_base_{reg['arquivo_sufixo']}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"hist_xlsx_{i}")
                with hd2:
                    st.download_button("📥 BAIXAR .CSV", data=reg["csv_data"], file_name=f"cadarn_base_{reg['arquivo_sufixo']}.csv", mime="text/csv", use_container_width=True, key=f"hist_csv_{i}")
                with hd3:
                    st.download_button("📋 AUDITORIA", data=reg["auditoria_data"], file_name=f"auditoria_{reg['arquivo_sufixo']}.txt", mime="text/plain", use_container_width=True, key=f"hist_txt_{i}")
                
                st.markdown("<hr style='border-color: var(--border-color); margin-top: 5px; margin-bottom: 25px;'>", unsafe_allow_html=True)