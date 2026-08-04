import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import altair as alt
import json

st.set_page_config(page_title="CRM Grupos & Propostas", page_icon="🏨", layout="wide")

st.markdown("""
    <style>
    @keyframes piscar {
        0% { opacity: 1; }
        50% { opacity: 0.3; }
        100% { opacity: 1; }
    }
    .alerta-piscando {
        animation: piscar 1.2s infinite;
        padding: 10px;
        border-radius: 5px;
        background-color: #ffcccc;
        color: #990000;
        font-weight: bold;
        text-align: center;
        margin-bottom: 10px;
        border: 1px solid #ff9999;
    }
    @media print {
        .stSidebar { display: none; }
        header { display: none; }
    }
    </style>
""", unsafe_allow_html=True)

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1_vvU_tgDtHCqtoKG4xR5XMfmnujGTXf7pndgg_aQoX0/edit?gid=0#gid=0"
URL_WEB_APP = "https://script.google.com/macros/s/AKfycbz7vQ65GWPeo1_qJpngvHkYG3G_GMmo_XYdsT-RSzcMisSHz70rtik3ftANwA3KGme1SQ/exec"

def obter_tipologias_compativeis(tipo_quarto):
    """Retorna as opções de tipologias compatíveis com o tipo de quarto selecionado"""
    if tipo_quarto == "Single" or tipo_quarto == "Duplo":
        return [
            "DBD / Standard (01 cama de casal)",
            "DBC / Standard (01 cama de casal e 01 cama de solteiro sobreposta)",
            "TWC / Standard (02 camas de solteiro)",
            "ROH / Superior (01 cama de casal)",
            "S2D / Superior (01 cama de casal e 01 cama de solteiro sobreposta)"
        ]
    elif tipo_quarto == "Triplo":
        return [
            "DBC / Standard (01 cama de casal e 01 cama de solteiro sobreposta)",
            "S2D / Superior (01 cama de casal e 01 cama de solteiro sobreposta)"
        ]
    return []

@st.cache_resource(ttl=300) 
def conectar_planilhas():
    credenciais = dict(st.secrets["gcp_service_account"])
    escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(credenciais, scopes=escopos)
    cliente = gspread.authorize(creds)
    
    planilha = cliente.open_by_url(URL_PLANILHA)
    aba_dados = planilha.worksheet("Dados")
    aba_usuarios = planilha.worksheet("Usuarios")
    
    try:
        aba_vendas_diretas = planilha.worksheet("Vendas_Diretas")
    except:
        aba_vendas_diretas = planilha.add_worksheet(title="Vendas_Diretas", rows=100, cols=20)
        aba_vendas_diretas.append_row(['ID', 'Data Envio', 'Empresa', 'Contato', 'E-mail', 'Telefone', 'Check-in', 'Check-out', 'Total RN Single', 'Total RN Duplo', 'Total RN Triplo', 'Tarifa Single', 'Tarifa Duplo', 'Tarifa Triplo', 'Receita Total', 'Status', 'Deadline', 'Motivo Recusa', 'Mapa de Quartos', 'Criado_Por'])

    try:
        aba_propostas = planilha.worksheet("Propostas")
    except:
        aba_propostas = planilha.add_worksheet(title="Propostas", rows=100, cols=14)
        aba_propostas.append_row(['ID_Proposta', 'Cliente', 'Email', 'Produtos_Contratados', 'Valor_Total', 'Status', 'Observacoes', 'Data_Criacao', 'Ultimo_Acesso', 'Nome_Usuario', 'Cargo_Usuario', 'Email_Usuario', 'Tel_Usuario', 'Link_Proposta'])

    return aba_dados, aba_vendas_diretas, aba_usuarios, aba_propostas

try:
    aba_dados, aba_vendas_diretas, aba_usuarios, aba_propostas = conectar_planilhas()
    
    @st.cache_data(ttl=60)
    def carregar_dados_gerais():
        todos_dados = aba_dados.get_all_values()
        if not todos_dados or len(todos_dados) <= 1:
            df_d = pd.DataFrame()
        else:
            h_d = [str(h).strip() if str(h).strip() != "" else f"Coluna_{i}" for i, h in enumerate(todos_dados[0])]
            df_d = pd.DataFrame(todos_dados[1:], columns=h_d)
            df_d['Origem_Fluxo'] = 'Equipe de Reservas'
            
        todos_vendas = aba_vendas_diretas.get_all_values()
        if not todos_vendas or len(todos_vendas) <= 1:
            df_v = pd.DataFrame()
        else:
            h_v = [str(h).strip() if str(h).strip() != "" else f"Coluna_{i}" for i, h in enumerate(todos_vendas[0])]
            df_v = pd.DataFrame(todos_vendas[1:], columns=h_v)
            df_v['Origem_Fluxo'] = 'Vendas Diretas'
            
        df_unificado = pd.concat([df_d, df_v], ignore_index=True)
        if not df_unificado.empty:
            df_unificado.columns = df_unificado.columns.str.strip()
            if 'Status' in df_unificado.columns:
                df_unificado['Status_Clean'] = df_unificado['Status'].astype(str).str.strip().str.lower()
            else:
                df_unificado['Status_Clean'] = ""
            if 'Motivo Recusa' not in df_unificado.columns:
                df_unificado['Motivo Recusa'] = 'Não informado'
            if 'Criado_Por' not in df_unificado.columns:
                df_unificado['Criado_Por'] = 'Sistema'
                
            cols_numericas = ['Total RN Single', 'Total RN Duplo', 'Total RN Triplo', 'Tarifa Single', 'Tarifa Duplo', 'Tarifa Triplo', 'Receita Total']
            for col in cols_numericas:
                if col in df_unificado.columns:
                    df_unificado[col] = pd.to_numeric(df_unificado[col].astype(str).str.replace('R$', '').str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
                    
        return df_unificado

    @st.cache_data(ttl=60)
    def carregar_propostas_cache():
        return aba_propostas.get_all_values()

    @st.cache_data(ttl=300)
    def carregar_usuarios_cache():
        return aba_usuarios.get_all_values()

    df = carregar_dados_gerais()
            
    propostas_valores = carregar_propostas_cache()
    if len(propostas_valores) > 1:
        header_prop = [h.strip() for h in propostas_valores[0]]
        df_propostas = pd.DataFrame(propostas_valores[1:], columns=header_prop)
    else:
        df_propostas = pd.DataFrame(columns=['ID_Proposta', 'Cliente', 'Email', 'Produtos_Contratados', 'Valor_Total', 'Status', 'Observacoes', 'Data_Criacao', 'Ultimo_Acesso', 'Link_Proposta', 'Nome_Usuario', 'Cargo_Usuario', 'Email_Usuario', 'Tel_Usuario'])

    todos_valores_user = carregar_usuarios_cache()
    if len(todos_valores_user) <= 1:
        usuarios_iniciais = [
            ["Amanda", "mudar@123", "Hotel", "Sim", "Analista de Distribuição e Reservas", "amanda@accor.com", "(11) 5085-5699"],
            ["Italo", "mudar@123", "Hotel", "Sim", "Analista de Distribuição e Reservas", "italo@accor.com", "(11) 5085-5699"],
            ["Amanda Ferrari", "mudar@123", "Vendas", "Sim", "Gerente de Vendas – Região Paulista & Jardins", "amanda.ferrari@accor.com", "(11) 99487-5023"],
            ["Elton", "mudar@123", "Vendas", "Sim", "Gerente de Contas / Account Manager", "elton.santos@accor.com", "(11) 94537-3303"],
            ["Catarina", "mudar@123", "Gerencial", "Não", "Gerente Geral", "catarina.costa@accor.com", "(11) 5085-5699"],
            ["Kessia", "mudar@123", "Gerencial", "Sim", "Subgerente", "kessia.gomes@accor.com", "(11) 5085-5699"]
        ]
        for u in usuarios_iniciais:
            aba_usuarios.append_row(u)
        todos_valores_user = aba_usuarios.get_all_values()

    header = [str(h).strip().lower() for h in todos_valores_user[0]]
    rows = todos_valores_user[1:]
    df_usuarios = pd.DataFrame(rows, columns=header)
            
except Exception as e:
    st.error(f"Erro ao conectar com as abas do Google Sheets: {e}")
    st.stop()

# Login
if "logado" not in st.session_state:
    st.session_state["logado"] = False
    st.session_state["usuario"] = ""
    st.session_state["perfil"] = ""
    st.session_state["cargo"] = ""
    st.session_state["email_user"] = ""
    st.session_state["tel_user"] = ""
    st.session_state["mudar_senha"] = False

if "form_version" not in st.session_state:
    st.session_state["form_version"] = 0

if not st.session_state["logado"]:
    st.title("🔐 Acesso ao Sistema de Grupos")
    lista_usuarios_validos = df_usuarios['usuario'].dropna().tolist()
    usuario_input = st.selectbox("Selecione seu Nome de Usuário", [""] + lista_usuarios_validos)
    senha_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar", type="primary"):
        if usuario_input == "":
            st.warning("Selecione um usuário.")
        else:
            user_row = df_usuarios[df_usuarios['usuario'] == usuario_input].iloc[0]
            senha_cadastrada = str(user_row['senha']).strip()
            if senha_input == senha_cadastrada:
                st.session_state["logado"] = True
                st.session_state["usuario"] = usuario_input
                st.session_state["perfil"] = str(user_row['perfil']).strip()
                st.session_state["cargo"] = str(user_row.get('cargo', 'Gerente Geral')).strip()
                st.session_state["email_user"] = str(user_row.get('email', 'catarina.costa@accor.com')).strip()
                st.session_state["tel_user"] = str(user_row.get('telefone', '(11) 5085-5699')).strip()
                
                if str(user_row['primeiro acesso']).strip() == "Sim" or senha_cadastrada == "mudar@123":
                    st.session_state["mudar_senha"] = True
                st.rerun()
            else:
                st.error("Senha incorreta!")
    st.stop()

if st.session_state["mudar_senha"]:
    st.title("🔑 Redefinição de Senha Obrigatória")
    with st.form("form_nova_senha"):
        nova_senha1 = st.text_input("Nova Senha", type="password")
        nova_senha2 = st.text_input("Confirme a Nova Senha", type="password")
        btn_trocar = st.form_submit_button("Salvar Nova Senha", type="primary")
        if btn_trocar:
            if nova_senha1 == "" or nova_senha1 != nova_senha2:
                st.error("As senhas não coincidem ou estão em branco.")
            else:
                idx = df_usuarios[df_usuarios['usuario'] == st.session_state["usuario"]].index[0] + 2
                aba_usuarios.update_cell(idx, 2, nova_senha1) 
                aba_usuarios.update_cell(idx, 4, "Não") 
                st.success("Senha alterada com sucesso!")
                st.session_state["mudar_senha"] = False
                st.cache_resource.clear()
                st.cache_data.clear()
                st.rerun()
    st.stop()

st.sidebar.button("Sair (Logout)", on_click=lambda: st.session_state.clear())

perfil = st.session_state["perfil"]
usuario_atual = st.session_state["usuario"]
st.sidebar.title(f"🏨 Olá, {usuario_atual}")
st.sidebar.caption(f"Perfil: {perfil}")

opcoes_menu = []
if perfil.lower() == "gerencial":
    opcoes_menu = ["📊 Dashboard & Analytics", "🛎️ Nova Solicitação (Reservas)", "💼 Gestão de Vendas & Propostas", "📑 Acompanhamento de Propostas", "👀 Follow-up", "⚙️ Gerenciar Usuários"]
elif perfil.lower() == "hotel":
    opcoes_menu = ["🛎️ Nova Solicitação (Reservas)", "👀 Follow-up"]
elif perfil.lower() == "vendas":
    opcoes_menu = ["📊 Dashboard & Analytics", "⚡ Nova Venda Direta", "💼 Gestão de Vendas & Propostas", "📑 Acompanhamento de Propostas", "👀 Follow-up"]

menu = st.sidebar.radio("Navegação:", opcoes_menu)

# 1. Dashboard & Analytics
if menu == "📊 Dashboard & Analytics":
    st.header("📊 Dashboard Executivo & Performance por Usuário")
    if st.button("🖨️ Exportar / Imprimir Relatório (PDF)"):
        st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
    if df.empty:
        st.info("Nenhum dado cadastrado.")
    else:
        df['Data_Envio_Dt'] = pd.to_datetime(df['Data Envio'], format='%d/%m/%Y', errors='coerce')
        df['Checkin_Dt'] = pd.to_datetime(df['Check-in'], format='%d/%m/%Y', errors='coerce')
        df['Mês/Ano Solicitação'] = df['Data_Envio_Dt'].dt.to_period('M').astype(str)
        df['Mês/Ano Competência (Check-in)'] = df['Checkin_Dt'].dt.to_period('M').astype(str)
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Filtros Avançados")
        tipo_filtro_data = st.sidebar.radio("Filtrar por:", ["Data de Solicitação", "Mês de Competência (Check-in)"])
        
        if tipo_filtro_data == "Data de Solicitação":
            meses_disp = sorted(df['Mês/Ano Solicitação'].dropna().unique().tolist(), reverse=True)
            mes_sel = st.sidebar.selectbox("Selecione o Mês de Solicitação:", ["Todos"] + meses_disp)
            df_dash = df[df['Mês/Ano Solicitação'] == mes_sel] if mes_sel != "Todos" else df
        else:
            meses_disp = sorted(df['Mês/Ano Competência (Check-in)'].dropna().unique().tolist(), reverse=True)
            mes_sel = st.sidebar.selectbox("Selecione a Competência (Check-in):", ["Todos"] + meses_disp)
            df_dash = df[df['Mês/Ano Competência (Check-in)'].astype(str) == mes_sel] if mes_sel != "Todos" else df

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Leads / Solicitações", len(df_dash))
        col2.metric("Propostas Enviadas", len(df_dash[df_dash['Status_Clean'].str.contains("cotação enviada|enviado", case=False, na=False)]))
        col3.metric("Confirmados", len(df_dash[df_dash['Status_Clean'].str.contains("confirmado", case=False, na=False)]))
        col4.metric("Recusados", len(df_dash[df_dash['Status_Clean'].str.contains("recusado", case=False, na=False)]))

        st.markdown("---")
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            st.subheader("📌 Comparativo de Origem (Reservas x Vendas Diretas)")
            if 'Origem_Fluxo' in df_dash.columns and not df_dash.empty:
                origem_counts = df_dash['Origem_Fluxo'].value_counts().reset_index()
                origem_counts.columns = ['Origem', 'Total']
                chart_origem = alt.Chart(origem_counts).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta(field="Total", type="quantitative"),
                    color=alt.Color(field="Origem", type="nominal", scale=alt.Scale(range=['#00703c', '#ffc107']))
                ).properties(height=300)
                st.altair_chart(chart_origem, use_container_width=True)

        with c_g2:
            st.subheader("🎯 Funil de Conversão")
            if not df_dash.empty:
                status_counts = df_dash['Status'].value_counts().reset_index()
                status_counts.columns = ['Status', 'Total']
                chart_status = alt.Chart(status_counts).mark_bar().encode(
                    x=alt.X('Total:Q', title='Quantidade'),
                    y=alt.Y('Status:N', sort='-x', title='Status'),
                    color=alt.Color('Status:N', legend=None)
                ).properties(height=300)
                st.altair_chart(chart_status, use_container_width=True)

# 2. Nova Solicitação (Reservas)
elif menu == "🛎️ Nova Solicitação (Reservas)":
    st.header("🛎️ Enviar Solicitação (Equipe de Reservas)")
    if st.button("🧹 Limpar / Novo Formulário"):
        st.session_state["form_version"] += 1
        st.rerun()

    v = st.session_state["form_version"]
    empresa = st.text_input("Empresa / Agência", key=f"input_empresa_{v}")
    col1, col2, col3 = st.columns(3)
    with col1: contato = st.text_input("Contato", key=f"input_contato_{v}")
    with col2: email = st.text_input("E-mail", key=f"input_email_{v}")
    with col3: telefone = st.text_input("Telefone", key=f"input_telefone_{v}")
        
    col_in, col_out = st.columns(2)
    with col_in: checkin = st.date_input("Primeiro Check-in", value=date.today(), key=f"input_checkin_{v}")
    with col_out: checkout = st.date_input("Último Check-out", value=date.today() + timedelta(days=1), key=f"input_checkout_{v}")
    
    dias = (checkout - checkin).days
    if dias > 0:
        datas_lista = [checkin + timedelta(days=i) for i in range(dias)]
        df_grid = pd.DataFrame({"Data": [d.strftime("%d/%m/%Y") for d in datas_lista], "Single": [0]*dias, "Duplo": [0]*dias, "Triplo": [0]*dias})
        df_editado = st.data_editor(df_grid, hide_index=True, use_container_width=True, key=f"grid_quartos_{v}")
        
        if st.button("🚀 Enviar Solicitação para Vendas", type="primary"):
            total_quartos = int(df_editado["Single"].sum() + df_editado["Duplo"].sum() + df_editado["Triplo"].sum())
            if empresa == "":
                st.error("O nome da Empresa é obrigatório.")
            elif total_quartos < 10:
                st.error(f"⚠️ Mínimo de 10 apartamentos. Total atual: {total_quartos}")
            else:
                id_unico = "G-" + datetime.now().strftime("%Y%m%d%H%M")
                nova_linha = [
                    id_unico, datetime.now().strftime("%d/%m/%Y"), empresa, contato, email, telefone, 
                    checkin.strftime("%d/%m/%Y"), checkout.strftime("%d/%m/%Y"), 
                    int(df_editado["Single"].sum()), int(df_editado["Duplo"].sum()), int(df_editado["Triplo"].sum()), 
                    0, 0, 0, 0, "Enviado para time de vendas", "", "", df_editado.to_json(orient='records'), usuario_atual
                ]
                aba_dados.append_row(nova_linha)
                st.success("✅ Solicitação enviada com sucesso!")
                st.cache_resource.clear()
                st.cache_data.clear()
                st.session_state["form_version"] += 1
                st.rerun()

# 2.1 Nova Venda Direta
elif menu == "⚡ Nova Venda Direta" and perfil.lower() == "vendas":
    st.header("⚡ Nova Venda / Proposta Direta (Time de Vendas)")
    if st.button("🧹 Limpar / Novo Formulário"):
        st.session_state["form_version"] += 1
        st.rerun()

    v = st.session_state["form_version"]
    empresa = st.text_input("Empresa / Agência", key=f"venda_empresa_{v}")
    col1, col2, col3 = st.columns(3)
    with col1: contato = st.text_input("Contato", key=f"venda_contato_{v}")
    with col2: email = st.text_input("E-mail", key=f"venda_email_{v}")
    with col3: telefone = st.text_input("Telefone", key=f"venda_telefone_{v}")
        
    col_in, col_out = st.columns(2)
    with col_in: checkin = st.date_input("Primeiro Check-in", value=date.today(), key=f"venda_checkin_{v}")
    with col_out: checkout = st.date_input("Último Check-out", value=date.today() + timedelta(days=1), key=f"venda_checkout_{v}")
    
    dias = (checkout - checkin).days
    if dias > 0:
        datas_lista = [checkin + timedelta(days=i) for i in range(dias)]
        df_grid = pd.DataFrame({"Data": [d.strftime("%d/%m/%Y") for d in datas_lista], "Single": [0]*dias, "Duplo": [0]*dias, "Triplo": [0]*dias})
        st.markdown("### 🛏️ Quantidade de Acomodações por Dia")
        df_editado = st.data_editor(df_grid, hide_index=True, use_container_width=True, key=f"venda_grid_quartos_{v}")
        
        rn_s = int(df_editado["Single"].sum())
        rn_d = int(df_editado["Duplo"].sum())
        rn_t = int(df_editado["Triplo"].sum())
        total_quartos = rn_s + rn_d + rn_t

        st.markdown("### 💰 1. Precificação e Tipologias por Tarifa NET")
        c1, c2, c3 = st.columns(3)
        t_single, t_duplo, t_triplo = 0.0, 0.0, 0.0
        tipos_s_sel, tipos_d_sel, tipos_t_sel = [], [], []

        with c1:
            if rn_s > 0:
                st.markdown("#### Diária Single")
                t_single = st.number_input("Tarifa Single (R$)", min_value=0.0, value=0.0, key=f"v_t_single_{v}")
                tipos_s_sel = st.multiselect("Tipologias Single:", options=obter_tipologias_compativeis("Single"), key=f"v_tipo_s_{v}")
        with c2:
            if rn_d > 0:
                st.markdown("#### Diária Dupla")
                t_duplo = st.number_input("Tarifa Duplo (R$)", min_value=0.0, value=0.0, key=f"v_t_duplo_{v}")
                tipos_d_sel = st.multiselect("Tipologias Duplo:", options=obter_tipologias_compativeis("Duplo"), key=f"v_tipo_d_{v}")
        with c3:
            if rn_t > 0:
                st.markdown("#### Diária Tripla")
                t_triplo = st.number_input("Tarifa Triplo (R$)", min_value=0.0, value=0.0, key=f"v_t_triplo_{v}")
                tipos_t_sel = st.multiselect("Tipologias Triplo:", options=obter_tipologias_compativeis("Triplo"), key=f"v_tipo_t_{v}")

        st.markdown("### 🍽️ 2. Produtos e Serviços Extras")
        st.write("Adicione refeições, maleiro, diárias de salas, etc.")
        df_extras_inicial = pd.DataFrame([{"Produto/Serviço": "", "Qtd": 0, "Valor Unitário (R$)": 0.0} for _ in range(3)])
        df_extras = st.data_editor(df_extras_inicial, num_rows="dynamic", hide_index=True, key=f"v_extras_{v}", use_container_width=True)

        st.markdown("---")
        novo_status = st.radio("Status Inicial:", ["Cotação enviada", "Confirmado"], horizontal=True, key=f"venda_status_{v}")
        
        novo_deadline = date.today() + timedelta(days=10)
        if novo_status != "Recusado":
            novo_deadline = st.date_input("Deadline para Resposta", value=date.today() + timedelta(days=10), key=f"venda_dead_{v}")
        
        motivos_recusa_lista = ["Preço", "Evento cancelado", "Categoria do Hotel", "Política de Pagamento", "Condições de Cancelamento", "Configuração dos Quartos", "Localização", "Sem retorno do cliente", "Outros"]
        motivo_recusa_input = ""
        if novo_status == "Recusado":
            motivo_recusa_input = st.selectbox("Motivo da Recusa:", motivos_recusa_lista, key=f"venda_sel_motivo_{v}")
            if motivo_recusa_input == "Outros":
                outro_texto = st.text_input("Especifique o motivo:", key=f"venda_txt_outro_{v}")
                if outro_texto: motivo_recusa_input = f"Outros: {outro_texto}"

        texto_botao = "💾 Registrar Recusa e Encerrar" if novo_status == "Recusado" else "🚀 Salvar Venda Direta e Gerar Proposta"
        
        if st.button(texto_botao, type="primary"):
            if empresa == "":
                st.error("O nome da Empresa é obrigatório.")
            elif total_quartos < 10:
                st.error(f"⚠️ Mínimo de 10 apartamentos. Total atual: {total_quartos}")
            else:
                str_tipos_s = ", ".join(tipos_s_sel) if tipos_s_sel else "Conforme disponibilidade"
                str_tipos_d = ", ".join(tipos_d_sel) if tipos_d_sel else "Conforme disponibilidade"
                str_tipos_t = ", ".join(tipos_t_sel) if tipos_t_sel else "Conforme disponibilidade"

                tabela_html = "<h4>Hospedagem (Com ISS 5%):</h4>"
                tabela_html += "<table><tr><th>Acomodação</th><th>Tipologia(s) Selecionada(s)</th><th>Qtd / RN</th><th>Valor Unit. NET</th><th>Subtotal (com ISS 5%)</th></tr>"
                
                receita_hospedagem = 0
                if rn_s > 0 and t_single > 0:
                    sub = (rn_s * t_single) * 1.05
                    receita_hospedagem += (rn_s * t_single)
                    tabela_html += f"<tr><td>Diária Single</td><td>{str_tipos_s}</td><td>{rn_s}</td><td>R$ {t_single:.2f}</td><td>R$ {sub:.2f}</td></tr>"
                if rn_d > 0 and t_duplo > 0:
                    sub = (rn_d * t_duplo) * 1.05
                    receita_hospedagem += (rn_d * t_duplo)
                    tabela_html += f"<tr><td>Diária Dupla</td><td>{str_tipos_d}</td><td>{rn_d}</td><td>R$ {t_duplo:.2f}</td><td>R$ {sub:.2f}</td></tr>"
                if rn_t > 0 and t_triplo > 0:
                    sub = (rn_t * t_triplo) * 1.05
                    receita_hospedagem += (rn_t * t_triplo)
                    tabela_html += f"<tr><td>Diária Tripla</td><td>{str_tipos_t}</td><td>{rn_t}</td><td>R$ {t_triplo:.2f}</td><td>R$ {sub:.2f}</td></tr>"
                tabela_html += "</table>"
                
                receita_extras = 0
                df_extras_valid = df_extras[df_extras["Produto/Serviço"].str.strip() != ""]
                if not df_extras_valid.empty:
                    tabela_html += "<br><h4>Serviços Extras:</h4>"
                    tabela_html += "<table><tr><th>Produto/Serviço</th><th>Qtd</th><th>Valor Unit.</th><th>Subtotal</th></tr>"
                    for _, row in df_extras_valid.iterrows():
                        nome = row["Produto/Serviço"]
                        qtd = int(row["Qtd"])
                        val = float(row["Valor Unitário (R$)"])
                        if qtd > 0:
                            sub = qtd * val
                            receita_extras += sub
                            tabela_html += f"<tr><td>{nome}</td><td>{qtd}</td><td>R$ {val:.2f}</td><td>R$ {sub:.2f}</td></tr>"
                    tabela_html += "</table>"
                
                receita_total = float((receita_hospedagem * 1.05) + receita_extras)
                id_unico = "V-" + datetime.now().strftime("%Y%m%d%H%M")
                
                nova_linha = [
                    id_unico, datetime.now().strftime("%d/%m/%Y"), empresa, contato, email, telefone, 
                    checkin.strftime("%d/%m/%Y"), checkout.strftime("%d/%m/%Y"), 
                    rn_s, rn_d, rn_t, t_single, t_duplo, t_triplo, receita_total, 
                    novo_status, novo_deadline.strftime("%d/%m/%Y") if novo_status != "Recusado" else "", motivo_recusa_input, df_editado.to_json(orient='records'), usuario_atual
                ]
                aba_vendas_diretas.append_row(nova_linha)
                
                id_prop = f"PROP-{id_unico}"
                data_hj = datetime.now().strftime("%d/%m/%Y")
                link_rastreavel = f"{URL_WEB_APP}?id={id_prop}&nome={empresa.replace(' ', '%20')}"
                
                u_cargo = str(st.session_state.get("cargo", "Gerente de Vendas"))
                u_email = str(st.session_state.get("email_user", "catarina.costa@accor.com"))
                u_tel = str(st.session_state.get("tel_user", "(11) 5085-5699"))

                propostas_atuais = aba_propostas.get_all_values()
                idx_proposta_existente = -1
                for idx_p, p_row in enumerate(propostas_atuais[1:], start=2):
                    if p_row[0] == id_prop:
                        idx_proposta_existente = idx_p
                        break
                
                nova_linha_proposta = [
                    str(id_prop), str(empresa), str(email), str(tabela_html), 
                    f"{receita_total:,.2f}", str(novo_status), "", str(data_hj), "",
                    str(usuario_atual), str(u_cargo), str(u_email), str(u_tel), str(link_rastreavel)
                ]

                if idx_proposta_existente != -1:
                    aba_propostas.update(f'A{idx_proposta_existente}:N{idx_proposta_existente}', [nova_linha_proposta])
                else:
                    aba_propostas.append_row(nova_linha_proposta)

                st.success("✅ Venda Direta salva e proposta gerada com sucesso!")
                if novo_status != "Recusado":
                    st.code(link_rastreavel)
                st.cache_resource.clear()
                st.cache_data.clear()

# 3. Gestão de Vendas & Proposta
elif menu == "💼 Gestão de Vendas & Propostas":
    st.header("💼 Tratativa, Precificação e Envio de Proposta")
    if perfil.lower() not in ["vendas", "gerencial"]:
        st.error("🔒 Acesso Restrito!")
    else:
        if df.empty:
            st.warning("Nenhum grupo cadastrado.")
        else:
            df_pendentes = df[~df['Status_Clean'].isin(['confirmado', 'recusado'])]
            
            if df_pendentes.empty:
                st.success("Nenhum grupo pendente no momento!")
            else:
                st.markdown("### 🔍 Filtrar Gestão por Status")
                status_disponiveis = ["Todos"] + sorted(df_pendentes['Status'].dropna().unique().tolist())
                status_filtro_sel = st.selectbox("Selecione o Status para filtrar na listagem abaixo:", status_disponiveis, key="filtro_status_gestao_principal")
                
                if status_filtro_sel != "Todos":
                    df_pendentes_filtrado = df_pendentes[df_pendentes['Status'] == status_filtro_sel]
                else:
                    df_pendentes_filtrado = df_pendentes

                if df_pendentes_filtrado.empty:
                    st.info(f"Nenhum grupo encontrado com o status: '{status_filtro_sel}'.")
                else:
                    if st.button("🧹 Limpar / Novo Formulário"):
                        st.session_state["form_version"] += 1
                        st.rerun()

                    v = st.session_state["form_version"]
                    opcoes = df_pendentes_filtrado['ID'].astype(str) + " - " + df_pendentes_filtrado['Empresa'] + " (" + df_pendentes_filtrado['Origem_Fluxo'] + " - Status: " + df_pendentes_filtrado['Status'] + ")"
                    grupo_sel = st.selectbox("Escolha o Grupo para tratar:", opcoes, key=f"sel_grupo_tratar_{v}")
                    id_sel = grupo_sel.split(" - ")[0]
                    linha_atual = df_pendentes_filtrado[df_pendentes_filtrado['ID'] == id_sel].iloc[0]
                    
                    st.markdown("---")
                    st.markdown("### 📋 Detalhes da Solicitação")
                    dc1, dc2, dc3 = st.columns(3)
                    with dc1:
                        st.write(f"**Empresa:** {linha_atual['Empresa']}")
                        st.write(f"**Contato:** {linha_atual['Contato']}")
                    with dc2:
                        st.write(f"**E-mail:** {linha_atual['E-mail']}")
                        st.write(f"**Telefone:** {linha_atual['Telefone']}")
                    with dc3:
                        st.write(f"**Período:** {linha_atual['Check-in']} até {linha_atual['Check-out']}")
                        st.write(f"**Origem:** {linha_atual.get('Origem_Fluxo', 'Reservas')}")
                    st.markdown("---")

                    propostas_atuais_l = aba_propostas.get_all_values()
                    id_prop_buscado = f"PROP-{id_sel}"
                    obs_ajuste_cliente = ""
                    for p_r in propostas_atuais_l[1:]:
                        if p_r[0] == id_prop_buscado and len(p_r) > 6 and p_r[6]:
                            obs_ajuste_cliente = p_r[6]
                            break

                    if obs_ajuste_cliente:
                        st.warning(f"💬 **Histórico / Solicitação de Ajuste do Cliente:** {obs_ajuste_cliente}")
                        with st.expander("🔍 Ver como estava a solicitação / valores anteriores"):
                            st.write(f"**Total RN Single anterior:** {linha_atual['Total RN Single']}")
                            st.write(f"**Total RN Duplo anterior:** {linha_atual['Total RN Duplo']}")
                            st.write(f"**Total RN Triplo anterior:** {linha_atual['Total RN Triplo']}")
                            st.write(f"**Tarifas anteriores:** Single: R$ {linha_atual.get('Tarifa Single', 0)} | Duplo: R$ {linha_atual.get('Tarifa Duplo', 0)} | Triplo: R$ {linha_atual.get('Tarifa Triplo', 0)}")

                    mapa_quartos_salvo = linha_atual.get('Mapa de Quartos', '')
                    checkin_dt = datetime.strptime(linha_atual['Check-in'], '%d/%m/%Y').date()
                    checkout_dt = datetime.strptime(linha_atual['Check-out'], '%d/%m/%Y').date()
                    dias_bloco = (checkout_dt - checkin_dt).days

                    st.markdown("### 🛏️ Atualizar Quantidade de Acomodações por Dia (Ajuste)")
                    if mapa_quartos_salvo and str(mapa_quartos_salvo).startswith("["):
                        try:
                            df_grid_inicial = pd.read_json(mapa_quartos_salvo)
                        except:
                            datas_l = [checkin_dt + timedelta(days=i) for i in range(dias_bloco)]
                            df_grid_inicial = pd.DataFrame({"Data": [d.strftime("%d/%m/%Y") for d in datas_l], "Single": [0]*dias_bloco, "Duplo": [0]*dias_bloco, "Triplo": [0]*dias_bloco})
                    else:
                        datas_l = [checkin_dt + timedelta(days=i) for i in range(dias_bloco)]
                        df_grid_inicial = pd.DataFrame({"Data": [d.strftime("%d/%m/%Y") for d in datas_l], "Single": [0]*dias_bloco, "Duplo": [0]*dias_bloco, "Triplo": [0]*dias_bloco})

                    df_editado_gestao = st.data_editor(df_grid_inicial, hide_index=True, use_container_width=True, key=f"g_grid_quartos_{v}")
                    
                    rn_s = int(df_editado_gestao["Single"].sum())
                    rn_d = int(df_editado_gestao["Duplo"].sum())
                    rn_t = int(df_editado_gestao["Triplo"].sum())

                    st.write(f"**Totais recalculados no período:** Single: {rn_s} | Duplo: {rn_d} | Triplo: {rn_t}")
                    
                    tarifa_single_salva = float(linha_atual.get('Tarifa Single', 0.0) or 0.0)
                    tarifa_duplo_salva = float(linha_atual.get('Tarifa Duplo', 0.0) or 0.0)
                    tarifa_triplo_salva = float(linha_atual.get('Tarifa Triplo', 0.0) or 0.0)

                    st.markdown("### 💰 1. Precificação e Tipologias por Tarifa NET")
                    c1, c2, c3 = st.columns(3)
                    t_single, t_duplo, t_triplo = 0.0, 0.0, 0.0
                    tipos_s_sel, tipos_d_sel, tipos_t_sel = [], [], []
                    
                    with c1:
                        if rn_s > 0:
                            st.markdown("#### Diária Single")
                            t_single = st.number_input("Tarifa Single (R$)", value=tarifa_single_salva, key=f"g_ts_{v}")
                            tipos_s_sel = st.multiselect("Tipologias Single:", options=obter_tipologias_compativeis("Single"), key=f"g_tipo_s_{v}")
                    with c2:
                        if rn_d > 0:
                            st.markdown("#### Diária Dupla")
                            t_duplo = st.number_input("Tarifa Duplo (R$)", value=tarifa_duplo_salva, key=f"g_td_{v}")
                            tipos_d_sel = st.multiselect("Tipologias Duplo:", options=obter_tipologias_compativeis("Duplo"), key=f"g_tipo_d_{v}")
                    with c3:
                        if rn_t > 0:
                            st.markdown("#### Diária Tripla")
                            t_triplo = st.number_input("Tarifa Triplo (R$)", value=tarifa_triplo_salva, key=f"g_tt_{v}")
                            tipos_t_sel = st.multiselect("Tipologias Triplo:", options=obter_tipologias_compativeis("Triplo"), key=f"g_tipo_t_{v}")

                    st.markdown("### 🍽️ 2. Produtos e Serviços Extras")
                    st.write("Adicione refeições, maleiro, diárias de salas, etc.")
                    df_extras_inicial = pd.DataFrame([{"Produto/Serviço": "", "Qtd": 0, "Valor Unitário (R$)": 0.0} for _ in range(3)])
                    df_extras = st.data_editor(df_extras_inicial, num_rows="dynamic", hide_index=True, key=f"g_extras_{v}", use_container_width=True)

                    st.markdown("---")
                    novo_status = st.radio("Status:", ["Cotação enviada", "Confirmado", "Recusado"], horizontal=True, key=f"radio_status_comercial_{v}")
                    
                    novo_deadline = date.today() + timedelta(days=10)
                    if novo_status != "Recusado":
                        novo_deadline = st.date_input("Deadline", value=date.today() + timedelta(days=10), key=f"input_deadline_comercial_{v}")
                    
                    motivos_recusa_lista = ["Preço", "Evento cancelado", "Categoria del Hotel", "Política de Pagamento", "Condições de Cancelamento", "Configuração dos Quartos", "Localização", "Sem retorno do cliente", "Outros"]
                    motivo_recusa_input = ""
                    if novo_status == "Recusado":
                        motivo_recusa_input = st.selectbox("Motivo da Recusa:", motivos_recusa_lista, key=f"sel_motivo_{v}")
                        if motivo_recusa_input == "Outros":
                            outro_texto = st.text_input("Especifique o motivo:", key=f"txt_outro_motivo_{v}")
                            if outro_texto: motivo_recusa_input = f"Outros: {outro_texto}"

                    texto_botao = "💾 Registrar Recusa e Encerrar" if novo_status == "Recusado" else "💾 Salvar e Gerar Link da Proposta"
                    
                    if st.button(texto_botao, type="primary"):
                        str_tipos_s = ", ".join(tipos_s_sel) if tipos_s_sel else "Conforme disponibilidade"
                        str_tipos_d = ", ".join(tipos_d_sel) if tipos_d_sel else "Conforme disponibilidade"
                        str_tipos_t = ", ".join(tipos_t_sel) if tipos_t_sel else "Conforme disponibilidade"

                        tabela_html = "<h4>Hospedagem (Com ISS 5%):</h4>"
                        tabela_html += "<table><tr><th>Acomodação</th><th>Tipologia(s) Selecionada(s)</th><th>Qtd / RN</th><th>Valor Unit. NET</th><th>Subtotal (com ISS 5%)</th></tr>"
                        
                        receita_hospedagem = 0
                        if rn_s > 0 and t_single > 0:
                            sub = (rn_s * t_single) * 1.05
                            receita_hospedagem += (rn_s * t_single)
                            tabela_html += f"<tr><td>Diária Single</td><td>{str_tipos_s}</td><td>{rn_s}</td><td>R$ {t_single:.2f}</td><td>R$ {sub:.2f}</td></tr>"
                        if rn_d > 0 and t_duplo > 0:
                            sub = (rn_d * t_duplo) * 1.05
                            receita_hospedagem += (rn_d * t_duplo)
                            tabela_html += f"<tr><td>Diária Dupla</td><td>{str_tipos_d}</td><td>{rn_d}</td><td>R$ {t_duplo:.2f}</td><td>R$ {sub:.2f}</td></tr>"
                        if rn_t > 0 and t_triplo > 0:
                            sub = (rn_t * t_triplo) * 1.05
                            receita_hospedagem += (rn_t * t_triplo)
                            tabela_html += f"<tr><td>Diária Tripla</td><td>{str_tipos_t}</td><td>{rn_t}</td><td>R$ {t_triplo:.2f}</td><td>R$ {sub:.2f}</td></tr>"
                        tabela_html += "</table>"
                        
                        receita_extras = 0
                        df_extras_valid = df_extras[df_extras["Produto/Serviço"].str.strip() != ""]
                        if not df_extras_valid.empty:
                            tabela_html += "<br><h4>Serviços Extras:</h4>"
                            tabela_html += "<table><tr><th>Produto/Serviço</th><th>Qtd</th><th>Valor Unit.</th><th>Subtotal</th></tr>"
                            for _, row in df_extras_valid.iterrows():
                                nome = row["Produto/Serviço"]
                                qtd = int(row["Qtd"])
                                val = float(row["Valor Unitário (R$)"])
                                if qtd > 0:
                                    sub = qtd * val
                                    receita_extras += sub
                                    tabela_html += f"<tr><td>{nome}</td><td>{qtd}</td><td>R$ {val:.2f}</td><td>R$ {sub:.2f}</td></tr>"
                            tabela_html += "</table>"
                        
                        receita_total = float((receita_hospedagem * 1.05) + receita_extras)
                        
                        alvo_aba = aba_vendas_diretas if str(id_sel).startswith("V-") else aba_dados
                        dados_alvo = alvo_aba.get_all_values()
                        linha_planilha = -1
                        for idx_l, row_l in enumerate(dados_alvo[1:], start=2):
                            if row_l[0] == id_sel:
                                linha_planilha = idx_l
                                break
                                
                        if linha_planilha != -1:
                            alvo_aba.update_cell(linha_planilha, 9, rn_s)
                            alvo_aba.update_cell(linha_planilha, 10, rn_d)
                            alvo_aba.update_cell(linha_planilha, 11, rn_t)
                            alvo_aba.update_cell(linha_planilha, 12, t_single)
                            alvo_aba.update_cell(linha_planilha, 13, t_duplo)
                            alvo_aba.update_cell(linha_planilha, 14, t_triplo)
                            alvo_aba.update_cell(linha_planilha, 15, receita_total)
                            alvo_aba.update_cell(linha_planilha, 16, novo_status)
                            alvo_aba.update_cell(linha_planilha, 17, novo_deadline.strftime("%d/%m/%Y") if novo_status != "Recusado" else "")
                            alvo_aba.update_cell(linha_planilha, 18, motivo_recusa_input)
                            alvo_aba.update_cell(linha_planilha, 19, df_editado_gestao.to_json(orient='records'))
                        
                        id_prop = f"PROP-{id_sel}"
                        data_hj = datetime.now().strftime("%d/%m/%Y")
                        link_rastreavel = f"{URL_WEB_APP}?id={id_prop}&nome={linha_atual['Empresa'].replace(' ', '%20')}"
                        
                        u_logado = str(st.session_state.get("usuario", "Equipe"))
                        u_cargo = str(st.session_state.get("cargo", "Gerente Geral"))
                        u_email = str(st.session_state.get("email_user", "catarina.costa@accor.com"))
                        u_tel = str(st.session_state.get("tel_user", "(11) 5085-5699"))

                        propostas_atuais = aba_propostas.get_all_values()
                        idx_proposta_existente = -1
                        for idx_p, p_row in enumerate(propostas_atuais[1:], start=2):
                            if p_row[0] == id_prop:
                                idx_proposta_existente = idx_p
                                break
                        
                        nova_linha_proposta = [
                            str(id_prop), str(linha_atual['Empresa']), str(linha_atual['E-mail']), str(tabela_html), 
                            f"{receita_total:,.2f}", str(novo_status), "", str(data_hj), "",
                            str(u_logado), str(u_cargo), str(u_email), str(u_tel), str(link_rastreavel)
                        ]

                        if idx_proposta_existente != -1:
                            aba_propostas.update(f'A{idx_proposta_existente}:N{idx_proposta_existente}', [nova_linha_proposta])
                        else:
                            aba_propostas.append_row(nova_linha_proposta)
                        
                        st.success(f"✅ Proposta atualizada e salva com sucesso! Status: {novo_status}")
                        if novo_status != "Recusado":
                            st.code(link_rastreavel)
                        st.cache_resource.clear()
                        st.cache_data.clear()
                        st.session_state["form_version"] += 1
                        st.rerun()

# 4. Acompanhamento de Propostas
elif menu == "📑 Acompanhamento de Propostas":
    st.header("📑 Acompanhamento e Reenvio de Propostas")
    if df_propostas.empty:
        st.info("Nenhuma proposta registrada.")
    else:
        colunas_reais = df_propostas.columns.tolist()
        
        for idx, row in df_propostas.iterrows():
            id_p = row['ID_Proposta'] if 'ID_Proposta' in colunas_reais else row.iloc[0] if len(row) > 0 else ''
            cliente_p = row['Cliente'] if 'Cliente' in colunas_reais else row.iloc[1] if len(row) > 1 else 'Cliente'
            status_p = row['Status'] if 'Status' in colunas_reais else row.iloc[5] if len(row) > 5 else ''
            
            val_tot = '0.00'
            if 'Valor_Total' in colunas_reais: val_tot = row['Valor_Total']
            elif 'Valor Total' in colunas_reais: val_tot = row['Valor Total']
            elif len(row) > 4: val_tot = row.iloc[4]
                
            criado_por = 'Usuário não identificado'
            if 'Nome_Usuario' in colunas_reais: criado_por = row['Nome_Usuario']
            elif 'Nome Usuario' in colunas_reais: criado_por = row['Nome Usuario']
            elif len(row) > 9: criado_por = row.iloc[9]
            
            link_proposta = ''
            if 'Link_Proposta' in colunas_reais: link_proposta = row['Link_Proposta']
            elif 'Link Proposta' in colunas_reais: link_proposta = row['Link Proposta']
            elif len(row) > 13: link_proposta = row.iloc[13]

            email_cliente = row['Email'] if 'Email' in colunas_reais else row.iloc[2] if len(row) > 2 else ''
            
            data_criacao = ''
            if 'Data_Criacao' in colunas_reais: data_criacao = row['Data_Criacao']
            elif 'Data Criacao' in colunas_reais: data_criacao = row['Data Criacao']
            elif len(row) > 7: data_criacao = row.iloc[7]

            obs = row['Observacoes'] if 'Observacoes' in colunas_reais else row.iloc[6] if len(row) > 6 else ''
            
            produtos_contratados = ''
            if 'Produtos_Contratados' in colunas_reais: produtos_contratados = row['Produtos_Contratados']
            elif 'Produtos Contratados' in colunas_reais: produtos_contratados = row['Produtos Contratados']
            elif len(row) > 3: produtos_contratados = row.iloc[3]

            if pd.isna(val_tot) or str(val_tot).strip() == '': val_tot = '0.00'
            if pd.isna(criado_por) or str(criado_por).strip() == '': criado_por = 'Usuário não identificado'
            if pd.isna(link_proposta): link_proposta = ''

            if str(criado_por).startswith("http"):
                link_temp = criado_por
                criado_por = link_proposta
                link_proposta = link_temp

            with st.expander(f"📌 {cliente_p} (ID: {id_p}) - Status: **{status_p}**"):
                st.write(f"**Empresa/Cliente:** {cliente_p} | **E-mail:** {email_cliente}")
                st.write(f"**Data de Criação:** {data_criacao}")
                st.write(f"**Valor Total:** R$ {val_tot} | **Criado por:** {criado_por}")
                
                if obs and str(obs).strip():
                    st.write(f"**Observações internas:** {obs}")

                st.markdown("---")
                st.markdown("##### 📄 Resumo da Proposta")
                if produtos_contratados and str(produtos_contratados).strip():
                    st.markdown(produtos_contratados, unsafe_allow_html=True)
                else:
                    st.info("Nenhum detalhe de produto registrado.")

                st.markdown("---")
                st.markdown("##### 🔗 Link da Proposta")
                if str(link_proposta).startswith("http"):
                    st.code(link_proposta)
                else:
                    possiveis_links = [str(x) for x in row.values if str(x).startswith("http")]
                    if possiveis_links:
                        st.code(possiveis_links[0])
                    else:
                        st.info("Link ainda não gerado para esta proposta.")

# 5. Follow-up
elif menu == "👀 Follow-up":
    st.header("👀 Acompanhamento da Operação")
    if df.empty:
        st.warning("Nenhum dado cadastrado.")
    else:
        t1, t2, t3 = st.tabs(["⚠️ Sem Tratativa", "⏳ Cotações em Aberto", "✅ Confirmados"])
        with t1: 
            df_sem_tratativa = df[df['Status_Clean'].str.contains("enviado|solicitação", case=False, na=False)]
            st.dataframe(df_sem_tratativa[['Data Envio', 'Empresa', 'Origem_Fluxo', 'Status']], use_container_width=True)
        with t2: 
            df_cotacoes = df[df['Status_Clean'].str.contains("cotação enviada|em ajuste", case=False, na=False)]
            st.dataframe(df_cotacoes[['Empresa', 'Deadline', 'Receita Total', 'Status']], use_container_width=True)
        with t3: 
            df_conf = df[df['Status_Clean'].str.contains("confirmado|aceita", case=False, na=False)]
            st.dataframe(df_conf[['Check-in', 'Check-out', 'Empresa', 'Receita Total', 'Status']], use_container_width=True)

# 6. Gerenciar Usuários
elif menu == "⚙️ Gerenciar Usuários":
    if perfil.lower() != "gerencial":
        st.error("🔒 Acesso Restrito! Apenas perfis gerenciais podem gerenciar usuários.")
    else:
        st.header("⚙️ Painel de Controle de Usuários")
        
        tab_lista, tab_novo, tab_editar = st.tabs(["👥 Lista de Usuários", "➕ Adicionar Novo Usuário", "✏️ Editar / Remover Usuário"])
        
        with tab_lista:
            st.subheader("Usuários Cadastrados no Sistema")
            colunas_publicas = [c for c in df_usuarios.columns if c.lower() != 'senha']
            st.dataframe(df_usuarios[colunas_publicas], use_container_width=True)
            
        with tab_novo:
            st.subheader("Cadastrar Novo Usuário")
            with st.form("form_novo_usuario"):
                novo_nome = st.text_input("Nome de Usuário / Login")
                nova_senha = st.text_input("Senha Inicial", type="password", value="mudar@123")
                novo_perfil = st.selectbox("Perfil de Acesso", ["Hotel", "Vendas", "Gerencial"])
                primeiro_acesso_opt = st.selectbox("Exigir Troca de Senha no 1º Acesso?", ["Sim", "Não"])
                novo_cargo = st.text_input("Cargo / Função", value="Analista de Distribuição e Reservas")
                novo_email = st.text_input("E-mail", value="accor@accor.com")
                novo_tel = st.text_input("Telefone", value="(11) 5085-5699")
                
                btn_cadastrar = st.form_submit_button("💾 Salvar Novo Usuário", type="primary")
                if btn_cadastrar:
                    if not novo_nome.strip():
                        st.error("O nome de usuário é obrigatório.")
                    else:
                        usuarios_atuais_lista = aba_usuarios.col_values(1)
                        if novo_nome in usuarios_atuais_lista:
                            st.error("Este nome de usuário já existe!")
                        else:
                            aba_usuarios.append_row([novo_nome, nova_senha, novo_perfil, primeiro_acesso_opt, novo_cargo, novo_email, novo_tel])
                            st.success(f"✅ Usuário '{novo_nome}' cadastrado com sucesso!")
                            st.cache_resource.clear()
                            st.cache_data.clear()
                            st.rerun()

        with tab_editar:
            st.subheader("Editar Senha, Perfil ou Remover Usuário")
            lista_usrs_ed = df_usuarios['usuario'].dropna().tolist()
            if not lista_usrs_ed:
                st.info("Nenhum usuário para gerenciar.")
            else:
                usr_selecionado = st.selectbox("Selecione o Usuário:", lista_usrs_ed)
                linha_usr_df = df_usuarios[df_usuarios['usuario'] == usr_selecionado].iloc[0]
                idx_planilha_usr = df_usuarios[df_usuarios['usuario'] == usr_selecionado].index[0] + 2
                
                with st.form("form_edicao_usuario"):
                    ed_senha = st.text_input("Nova Senha (deixe em branco para manter a atual)", type="password")
                    ed_perfil = st.selectbox("Perfil", ["Hotel", "Vendas", "Gerencial"], index=["Hotel", "Vendas", "Gerencial"].index(linha_usr_df['perfil']) if linha_usr_df['perfil'] in ["Hotel", "Vendas", "Gerencial"] else 0)
                    ed_pri_acesso = st.selectbox("Exigir Troca de Senha?", ["Sim", "Não"], index=0 if str(linha_usr_df.get('primeiro acesso', 'Sim')) == "Sim" else 1)
                    ed_cargo = st.text_input("Cargo", value=str(linha_usr_df.get('cargo', '')))
                    ed_email = st.text_input("E-mail", value=str(linha_usr_df.get('email', '')))
                    ed_tel = st.text_input("Telefone", value=str(linha_usr_df.get('telefone', '')))
                    
                    c_btn1, c_btn2 = st.columns(2)
                    with c_btn1:
                        btn_salvar_alt = st.form_submit_button("💾 Salvar Alterações", type="primary")
                    with c_btn2:
                        btn_remover = st.form_submit_button("🗑️ Remover Usuário")
                        
                    if btn_salvar_alt:
                        if ed_senha.strip():
                            aba_usuarios.update_cell(idx_planilha_usr, 2, ed_senha.strip())
                        aba_usuarios.update_cell(idx_planilha_usr, 3, ed_perfil)
                        aba_usuarios.update_cell(idx_planilha_usr, 4, ed_pri_acesso)
                        aba_usuarios.update_cell(idx_planilha_usr, 5, ed_cargo)
                        aba_usuarios.update_cell(idx_planilha_usr, 6, ed_email)
                        aba_usuarios.update_cell(idx_planilha_usr, 7, ed_tel)
                        st.success(f"✅ Alterações salvas para o usuário '{usr_selecionado}'!")
                        st.cache_resource.clear()
                        st.cache_data.clear()
                        st.rerun()
                        
                    if btn_remover:
                        if usr_selecionado == usuario_atual:
                            st.error("⚠️ Você não pode remover seu próprio usuário logado ativamente.")
                        else:
                            aba_usuarios.delete_rows(idx_planilha_usr)
                            st.success(f"🗑️ Usuário '{usr_selecionado}' removido com sucesso!")
                            st.cache_resource.clear()
                            st.cache_data.clear()
                            st.rerun()
