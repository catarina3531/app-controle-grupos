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
                
            # Tratamento de colunas numéricas para evitar erros de conversão
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
        df_propostas = pd.DataFrame(columns=['ID_Proposta', 'Cliente', 'Email', 'Produtos_Contratados', 'Valor_Total', 'Status', 'Observacoes', 'Data_Criacao', 'Ultimo_Acesso', 'Link_Proposta', 'Nome_Usuario'])

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
        col2.metric("Propostas Enviadas", len(df_dash[df_dash['Status_Clean'].str.contains("cotação enviada", case=False, na=False)]))
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

        st.markdown("---")
        st.subheader("👥 Relatório de Atividade por Usuário (Solicitações, Propostas & Conversões)")
        
        if not df_dash.empty:
            solic_por_usuario = df_dash.groupby('Criado_Por').size().reset_index(name='Total Solicitações')
            conf_por_usuario = df_dash[df_dash['Status_Clean'].str.contains("confirmado", case=False, na=False)].groupby('Criado_Por').size().reset_index(name='Confirmados')
            
            if not df_propostas.empty and 'Nome_Usuario' in df_propostas.columns:
                prop_por_usuario = df_propostas.groupby('Nome_Usuario').size().reset_index(name='Propostas Enviadas')
            else:
                prop_por_usuario = pd.DataFrame(columns=['Nome_Usuario', 'Propostas Enviadas'])
                
            tabela_usuarios = pd.merge(solic_por_usuario, prop_por_usuario, left_on='Criado_Por', right_on='Nome_Usuario', how='outer').fillna(0)
            if 'Nome_Usuario' in tabela_usuarios.columns:
                tabela_usuarios = tabela_usuarios.drop(columns=['Nome_Usuario'])
            tabela_usuarios = pd.merge(tabela_usuarios, conf_por_usuario, on='Criado_Por', how='left').fillna(0)
            tabela_usuarios.columns = ['Usuário / Vendedor', 'Solicitações Criadas', 'Propostas Enviadas', 'Confirmados']
            
            st.dataframe(tabela_usuarios, use_container_width=True)
        else:
            st.info("Sem dados para exibir na tabela por usuário.")

        st.markdown("---")
        c_g3, c_g4 = st.columns(2)

        with c_g3:
            st.subheader("❌ Percentual de Motivos de Recusa")
            df_recusados = df_dash[df_dash['Status_Clean'].str.contains("recusado", case=False, na=False)]
            if not df_recusados.empty and 'Motivo Recusa' in df_recusados.columns:
                motivo_counts = df_recusados['Motivo Recusa'].value_counts().reset_index()
                motivo_counts.columns = ['Motivo', 'Total']
                chart_motivo = alt.Chart(motivo_counts).mark_arc().encode(
                    theta=alt.Theta(field="Total", type="quantitative"),
                    color=alt.Color(field="Motivo", type="nominal")
                ).properties(height=300)
                st.altair_chart(chart_motivo, use_container_width=True)
            else:
                st.info("Nenhum dado de recusa registrado.")

        with c_g4:
            st.subheader("📈 Receita Confirmada por Mês de Competência (Check-in)")
            df_confirmados = df_dash[df_dash['Status_Clean'].str.contains("confirmado", case=False, na=False)]
            if not df_confirmados.empty:
                df_confirmados['Receita Total'] = pd.to_numeric(df_confirmados['Receita Total'], errors='coerce').fillna(0)
                rec_mes = df_confirmados.groupby('Mês/Ano Competência (Check-in)')['Receita Total'].sum().reset_index()
                chart_rec = alt.Chart(rec_mes).mark_line(point=True).encode(
                    x='Mês/Ano Competência (Check-in):N',
                    y='Receita Total:Q',
                    tooltip=['Mês/Ano Competência (Check-in)', 'Receita Total']
                ).properties(height=300)
                st.altair_chart(chart_rec, use_container_width=True)
            else:
                st.info("Nenhuma receita confirmada no período.")

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
                st.error(f"⚠️ Solicitação não permitida! O total de apartamentos solicitados é {total_quartos}. Mínimo de 10 aptos.")
            else:
                id_unico = "G-" + datetime.now().strftime("%Y%m%d%H%M")
                nova_linha = [
                    id_unico, datetime.now().strftime("%d/%m/%Y"), empresa, contato, email, telefone, 
                    checkin.strftime("%d/%m/%Y"), checkout.strftime("%d/%m/%Y"), 
                    int(df_editado["Single"].sum()), int(df_editado["Duplo"].sum()), int(df_editado["Triplo"].sum()), 
                    0, 0, 0, 0, "Enviado para time de vendas", "", "", df_editado.to_json(orient='records'), usuario_atual
                ]
                aba_dados.append_row(nova_linha)
                st.success("✅ Solicitação enviada com sucesso para a fila de vendas!")
                st.cache_resource.clear()
                st.cache_data.clear()
                st.session_state["form_version"] += 1
                st.rerun()

# 2.1 Nova Venda Direta
elif menu == "⚡ Nova Venda Direta" and perfil.lower() == "vendas":
    st.header("⚡ Nova Venda / Proposta Direta (Time de Vendas)")
    st.info("Utilize esta tela quando a solicitação e a precificação forem feitas diretamente por você.")

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
        df_editado = st.data_editor(df_grid, hide_index=True, use_container_width=True, key=f"venda_grid_quartos_{v}")
        
        rn_s = int(df_editado["Single"].sum())
        rn_d = int(df_editado["Duplo"].sum())
        rn_t = int(df_editado["Triplo"].sum())
        total_quartos = rn_s + rn_d + rn_t
        
        st.subheader("Precificação & Tarifas (NET)")
        tc1, tc2, tc3 = st.columns(3)
        with tc1: t_single = st.number_input("Tarifa Single (R$)", min_value=0.0, value=0.0, key=f"venda_ts_{v}")
        with tc2: t_duplo = st.number_input("Tarifa Duplo (R$)", min_value=0.0, value=0.0, key=f"venda_td_{v}")
        with tc3: t_triplo = st.number_input("Tarifa Triplo (R$)", min_value=0.0, value=0.0, key=f"venda_tt_{v}")
        
        novo_status = st.radio("Status Inicial:", ["Cotação enviada", "Confirmado"], horizontal=True, key=f"venda_status_{v}")
        novo_deadline = st.date_input("Deadline para Resposta", value=date.today(), key=f"venda_dead_{v}")
        
        if st.button("🚀 Salvar Venda Direta e Gerar Proposta", type="primary"):
            if empresa == "":
                st.error("O nome da Empresa é obrigatório.")
            elif total_quartos < 10:
                st.error(f"⚠️ Total de apartamentos solicitados é {total_quartos}. Mínimo de 10 aptos.")
            else:
                receita_hospedagem = (rn_s * t_single) + (rn_d * t_duplo) + (rn_t * t_triplo)
                receita_total = float(receita_hospedagem * 1.05)
                
                id_unico = "V-" + datetime.now().strftime("%Y%m%d%H%M")
                
                nova_linha = [
                    id_unico, datetime.now().strftime("%d/%m/%Y"), empresa, contato, email, telefone, 
                    checkin.strftime("%d/%m/%Y"), checkout.strftime("%d/%m/%Y"), 
                    rn_s, rn_d, rn_t, t_single, t_duplo, t_triplo, receita_total, 
                    novo_status, novo_deadline.strftime("%d/%m/%Y"), "", df_editado.to_json(orient='records'), usuario_atual
                ]
                aba_vendas_diretas.append_row(nova_linha)
                
                tabela_html = f"<h4>Discriminação da Hospedagem (Com ISS 5%):</h4>"
                tabela_html += f"<table><tr><th>Acomodação</th><th>Qtd / RN</th><th>Valor Unit. NET</th><th>Subtotal (com ISS 5%)</th></tr>"
                if rn_s > 0 and t_single > 0: tabela_html += f"<tr><td>Diária Single</td><td>{rn_s}</td><td>R$ {t_single:.2f}</td><td>R$ {(rn_s * t_single * 1.05):.2f}</td></tr>"
                if rn_d > 0 and t_duplo > 0: tabela_html += f"<tr><td>Diária Dupla</td><td>{rn_d}</td><td>R$ {t_duplo:.2f}</td><td>R$ {(rn_d * t_duplo * 1.05):.2f}</td></tr>"
                if rn_t > 0 and t_triplo > 0: tabela_html += f"<tr><td>Diária Tripla</td><td>{rn_t}</td><td>R$ {t_triplo:.2f}</td><td>R$ {(rn_t * t_triplo * 1.05):.2f}</td></tr>"
                tabela_html += "</table>"
                
                id_prop = f"PROP-{id_unico}"
                link_rastreavel = f"{URL_WEB_APP}?id={id_prop}&nome={empresa.replace(' ', '%20')}"
                valor_total_formatado = f"{receita_total:,.2f}"
                data_hj = datetime.now().strftime("%d/%m/%Y")
                
                u_cargo = str(st.session_state.get("cargo", "Gerente de Vendas"))
                u_email = str(st.session_state.get("email_user", "catarina.costa@accor.com"))
                u_tel = str(st.session_state.get("tel_user", "(11) 5085-5699"))

                aba_propostas.append_row([
                    str(id_prop), str(empresa), str(email), str(tabela_html), 
                    str(valor_total_formatado), str(novo_status), "", str(data_hj), "",
                    str(usuario_atual), str(u_cargo), str(u_email), str(u_tel), str(link_rastreavel)
                ])

                st.success("✅ Venda Direta registrada e proposta gerada com sucesso!")
                st.markdown("### 🔗 Link Inteligente para Envio:")
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
                if st.button("🧹 Limpar / Novo Formulário"):
                    st.session_state["form_version"] += 1
                    st.rerun()

                v = st.session_state["form_version"]
                opcoes = df_pendentes['ID'].astype(str) + " - " + df_pendentes['Empresa'] + " (" + df_pendentes['Origem_Fluxo'] + ")"
                grupo_sel = st.selectbox("Escolha o Grupo para tratar:", opcoes, key=f"sel_grupo_tratar_{v}")
                id_sel = grupo_sel.split(" - ")[0]
                linha_atual = df_pendentes[df_pendentes['ID'] == id_sel].iloc[0]
                
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

                rn_s = int(linha_atual['Total RN Single'] or 0)
                rn_d = int(linha_atual['Total RN Duplo'] or 0)
                rn_t = int(linha_atual['Total RN Triplo'] or 0)
                
                st.subheader("1. Tarifas de Hospedagem (NET)")
                c1, c2, c3 = st.columns(3)
                t_single, t_duplo, t_triplo = 0.0, 0.0, 0.0
                
                with c1:
                    if rn_s > 0: t_single = st.number_input("Tarifa Single (R$)", value=float(linha_atual.get('Tarifa Single', 0.0) or 0.0), key=f"val_t_single_{v}")
                with c2:
                    if rn_d > 0: t_duplo = st.number_input("Tarifa Duplo (R$)", value=float(linha_atual.get('Tarifa Duplo', 0.0) or 0.0), key=f"val_t_duplo_{v}")
                with c3:
                    if rn_t > 0: t_triplo = st.number_input("Tarifa Triplo (R$)", value=float(linha_atual.get('Tarifa Triplo', 0.0) or 0.0), key=f"val_t_triplo_{v}")
                
                novo_status = st.radio("Status:", ["Cotação enviada", "Confirmado", "Recusado"], horizontal=True, key=f"radio_status_comercial_{v}")
                novo_deadline = st.date_input("Deadline", value=date.today(), key=f"input_deadline_comercial_{v}")
                
                motivo_recusa_input = ""
                if novo_status == "Recusado":
                    motivo_recusa_input = st.selectbox("Motivo da Recusa:", ["Preço Alto", "Falta de Disponibilidade", "Concorrência", "Cancelado pelo Cliente", "Outros"], key=f"sel_motivo_{v}")

                if st.button("💾 Salvar e Gerar Link da Proposta", type="primary"):
                    receita_hospedagem = (rn_s * t_single) + (rn_d * t_duplo) + (rn_t * t_triplo)
                    receita_total = float(receita_hospedagem * 1.05)
                    
                    alvo_aba = aba_vendas_diretas if str(id_sel).startswith("V-") else aba_dados
                    dados_alvo = alvo_aba.get_all_values()
                    linha_planilha = -1
                    for idx_l, row_l in enumerate(dados_alvo[1:], start=2):
                        if row_l[0] == id_sel:
                            linha_planilha = idx_l
                            break
                            
                    if linha_planilha != -1:
                        alvo_aba.update_cell(linha_planilha, 12, t_single)
                        alvo_aba.update_cell(linha_planilha, 13, t_duplo)
                        alvo_aba.update_cell(linha_planilha, 14, t_triplo)
                        alvo_aba.update_cell(linha_planilha, 15, receita_total)
                        alvo_aba.update_cell(linha_planilha, 16, novo_status)
                        alvo_aba.update_cell(linha_planilha, 17, novo_deadline.strftime("%d/%m/%Y") if novo_status == "Cotação enviada" else "")
                        alvo_aba.update_cell(linha_planilha, 18, motivo_recusa_input)
                    
                    tabela_html = f"<h4>Discriminação da Hospedagem (Com ISS 5%):</h4>"
                    tabela_html += f"<table><tr><th>Acomodação</th><th>Qtd / RN</th><th>Valor Unit. NET</th><th>Subtotal (com ISS 5%)</th></tr>"
                    if rn_s > 0 and t_single > 0: tabela_html += f"<tr><td>Diária Single</td><td>{rn_s}</td><td>R$ {t_single:.2f}</td><td>R$ {(rn_s * t_single * 1.05):.2f}</td></tr>"
                    if rn_d > 0 and t_duplo > 0: tabela_html += f"<tr><td>Diária Dupla</td><td>{rn_d}</td><td>R$ {t_duplo:.2f}</td><td>R$ {(rn_d * t_duplo * 1.05):.2f}</td></tr>"
                    if rn_t > 0 and t_triplo > 0: tabela_html += f"<tr><td>Diária Tripla</td><td>{rn_t}</td><td>R$ {t_triplo:.2f}</td><td>R$ {(rn_t * t_triplo * 1.05):.2f}</td></tr>"
                    tabela_html += "</table>"
                    
                    id_prop = f"PROP-{id_sel}"
                    data_hj = datetime.now().strftime("%d/%m/%Y")
                    link_rastreavel = f"{URL_WEB_APP}?id={id_prop}&nome={linha_atual['Empresa'].replace(' ', '%20')}"
                    
                    u_logado = str(st.session_state.get("usuario", "Equipe"))
                    u_cargo = str(st.session_state.get("cargo", "Gerente Geral"))
                    u_email = str(st.session_state.get("email_user", "catarina.costa@accor.com"))
                    u_tel = str(st.session_state.get("tel_user", "(11) 5085-5699"))

                    valor_total_formatado = f"{receita_total:,.2f}"

                    propostas_atuais = aba_propostas.get_all_values()
                    achou = False
                    for idx_p, p_row in enumerate(propostas_atuais[1:], start=2):
                        if p_row[0] == id_prop:
                            aba_propostas.update(f'A{idx_p}:N{idx_p}', [[
                                str(id_prop), str(linha_atual['Empresa']), str(linha_atual['E-mail']), str(tabela_html), 
                                str(valor_total_formatado), str(novo_status), "", str(data_hj), "",
                                str(u_logado), str(u_cargo), str(u_email), str(u_tel), str(link_rastreavel)
                            ]])
                            achou = True
                            break
                    
                    if not achou:
                        aba_propostas.append_row([
                            str(id_prop), str(linha_atual['Empresa']), str(linha_atual['E-mail']), str(tabela_html), 
                            str(valor_total_formatado), str(novo_status), "", str(data_hj), "",
                            str(u_logado), str(u_cargo), str(u_email), str(u_tel), str(link_rastreavel)
                        ])
                    
                    st.success(f"✅ Proposta gerada/atualizada com sucesso! Status: {novo_status}")
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
        for idx, row in df_propostas.iterrows():
            id_p = row.get('ID_Proposta', '')
            cliente_p = row.get('Cliente', 'Cliente')
            link_proposta = row.get('Link_Proposta', '')
            with st.expander(f"📌 {cliente_p} (ID: {id_p}) - Status: **{row.get('Status', '')}**"):
                st.write(f"**Valor Total:** R$ {row.get('Valor_Total', '0.00')} | **Criado por:** {row.get('Nome_Usuario', '')}")
                st.code(link_proposta)

# 5. Follow-up
elif menu == "👀 Follow-up":
    st.header("👀 Acompanhamento da Operação")
    if df.empty:
        st.warning("Nenhum dado cadastrado.")
    else:
        t1, t2, t3 = st.tabs(["⚠️ Sem Tratativa", "⏳ Cotações em Aberto", "✅ Confirmados"])
        with t1: st.dataframe(df[df['Status_Clean'].str.contains("enviado", na=False)][['Data Envio', 'Empresa', 'Origem_Fluxo']], use_container_width=True)
        with t2: st.dataframe(df[df['Status_Clean'].str.contains("cotação enviada", case=False, na=False)][['Empresa', 'Deadline', 'Receita Total']], use_container_width=True)
        with t3: st.dataframe(df[df['Status_Clean'].str.contains("confirmado", case=False, na=False)][['Check-in', 'Check-out', 'Empresa', 'Receita Total']], use_container_width=True)

# 6. Gerenciar Usuários
elif menu == "⚙️ Gerenciar Usuários" and perfil.lower() == "gerencial":
    st.header("⚙️ Painel de Controle de Usuários")
    colunas_publicas = [c for c in df_usuarios.columns if c.lower() != 'senha']
    st.dataframe(df_usuarios[colunas_publicas], use_container_width=True)
