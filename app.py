import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import altair as alt

st.set_page_config(page_title="CRM Grupos", page_icon="🏨", layout="wide")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1_vvU_tgDtHCqtoKG4xR5XMfmnujGTXf7pndgg_aQoX0/edit?gid=0#gid=0"

@st.cache_resource(ttl=60) 
def conectar_planilha():
    credenciais = dict(st.secrets["gcp_service_account"])
    escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(credenciais, scopes=escopos)
    cliente = gspread.authorize(creds)
    aba = cliente.open_by_url(URL_PLANILHA).sheet1
    return aba

try:
    aba_dados = conectar_planilha()
    dados_planilha = aba_dados.get_all_records(expected_headers=[
        'ID', 'Data Envio', 'Empresa', 'Contato', 'E-mail', 'Telefone', 
        'Check-in', 'Check-out', 'Total RN Single', 'Total RN Duplo', 'Total RN Triplo', 
        'Tarifa Single', 'Tarifa Duplo', 'Tarifa Triplo', 'Receita Total', 
        'Status', 'Deadline', 'Motivo Recusa', 'Mapa de Quartos'
    ])
    df = pd.DataFrame(dados_planilha)
    if not df.empty:
        df.columns = df.columns.str.strip() # Remove espaços invisíveis
except Exception as e:
    st.error(f"Erro ao conectar com o banco de dados: {e}")
    st.stop()

# ------------------------------------------------
# Sistema de Login Simples
# ------------------------------------------------
if "logado" not in st.session_state:
    st.session_state["logado"] = False
    st.session_state["perfil"] = ""

if not st.session_state["logado"]:
    st.title("🔐 Acesso ao Sistema de Grupos")
    senha = st.text_input("Digite sua senha de acesso", type="password")
    
    if st.button("Entrar", type="primary"):
        if senha == "hotel123":
            st.session_state["logado"] = True
            st.session_state["perfil"] = "Hotel"
            st.rerun()
        elif senha == "vendas123":
            st.session_state["logado"] = True
            st.session_state["perfil"] = "Vendas"
            st.rerun()
        elif senha == "gerente123":
            st.session_state["logado"] = True
            st.session_state["perfil"] = "Gerencial"
            st.rerun()
        else:
            st.error("Senha incorreta!")
    st.stop() 

# Botão de Sair
st.sidebar.button("Sair (Logout)", on_click=lambda: st.session_state.clear())

# ------------------------------------------------
# Controle de Permissões (Menu)
# ------------------------------------------------
perfil = st.session_state["perfil"]
st.sidebar.title(f"🏨 Menu ({perfil})")

opcoes_menu = []
if perfil == "Gerencial":
    opcoes_menu = ["📊 Dashboard", "🛎️ Nova Solicitação", "💼 Gestão de Vendas", "👀 Follow-up"]
elif perfil == "Hotel":
    opcoes_menu = ["🛎️ Nova Solicitação", "👀 Follow-up"]
elif perfil == "Vendas":
    opcoes_menu = ["📊 Dashboard", "💼 Gestão de Vendas"]

menu = st.sidebar.radio("Navegação:", opcoes_menu)

# ------------------------------------------------
# 1. Dashboard Gerencial
# ------------------------------------------------
if menu == "📊 Dashboard":
    st.header("📊 Visão Gerencial de Grupos")
    if df.empty:
        st.info("Nenhum dado cadastrado.")
    else:
        df['Data Envio'] = pd.to_datetime(df['Data Envio'], format='%d/%m/%Y', errors='coerce')
        df['Mês/Ano'] = df['Data Envio'].dt.to_period('M').astype(str)
        meses_disponiveis = sorted(df['Mês/Ano'].dropna().unique().tolist(), reverse=True)
        mes_selecionado = st.selectbox("Filtrar por Mês de Entrada:", ["Todos"] + meses_disponiveis)
        
        df_dash = df[df['Mês/Ano'] == mes_selecionado] if mes_selecionado != "Todos" else df

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📌 Leads Recebidos", len(df_dash))
        col2.metric("📤 Propostas Enviadas", len(df_dash[df_dash['Status'].astype(str).str.contains("cotação enviada", case=False, na=False)]))
        col3.metric("✅ Confirmados", len(df_dash[df_dash['Status'].astype(str).str.contains("confirmado", case=False, na=False)]))
        col4.metric("❌ Recusados", len(df_dash[df_dash['Status'].astype(str).str.contains("recusado", case=False, na=False)]))
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            status_contagem = df_dash['Status'].value_counts().reset_index()
            status_contagem.columns = ['Status', 'Quantidade']
            grafico_barras = alt.Chart(status_contagem).mark_bar(color='#4CAF50').encode(x='Quantidade', y=alt.Y('Status', sort='-x'))
            st.altair_chart(grafico_barras, use_container_width=True)
            
        with c2:
            df_recusados = df_dash[df_dash['Status'].astype(str).str.contains("recusado", case=False, na=False)]
            if not df_recusados.empty:
                motivos = df_recusados['Motivo Recusa'].value_counts().reset_index()
                motivos.columns = ['Motivo', 'Quantidade']
                grafico_pizza = alt.Chart(motivos).mark_arc(innerRadius=50).encode(theta='Quantidade', color='Motivo', tooltip=['Motivo', 'Quantidade'])
                st.altair_chart(grafico_pizza, use_container_width=True)
            else:
                st.info("Nenhuma recusa neste período.")

# ------------------------------------------------
# 2. Nova Solicitação (Hotel)
# ------------------------------------------------
elif menu == "🛎️ Nova Solicitação":
    st.header("🛎️ Enviar Grupo para Vendas")
    st.markdown("Defina a data global do grupo e informe a quantidade de quartos por dia.")

    empresa = st.text_input("Empresa / Agência")
    col1, col2, col3 = st.columns(3)
    with col1: contato = st.text_input("Contato")
    with col2: email = st.text_input("E-mail")
    with col3: telefone = st.text_input("Telefone")
        
    st.subheader("Bloco Diário de Quartos (Room Block)")
    col_in, col_out = st.columns(2)
    with col_in: checkin = st.date_input("Primeiro Check-in", value=date.today())
    with col_out: checkout = st.date_input("Último Check-out", value=date.today() + timedelta(days=1))
    
    dias = (checkout - checkin).days
    
    if dias > 0:
        datas_lista = [checkin + timedelta(days=i) for i in range(dias)]
        dados_dias = {"Data": [d.strftime("%d/%m/%Y") for d in datas_lista], "Single": [0]*dias, "Duplo": [0]*dias, "Triplo": [0]*dias}
        df_grid = pd.DataFrame(dados_dias)
        
        st.markdown("**Preencha a quantidade de quartos necessária para cada dia:**")
        df_editado = st.data_editor(df_grid, hide_index=True, use_container_width=True)
        
        tot_sin = int(df_editado["Single"].sum())
        tot_dup = int(df_editado["Duplo"].sum())
        tot_tri = int(df_editado["Triplo"].sum())
        
        st.info(f"**Resumo do Pedido:** {tot_sin} RN Single | {tot_dup} RN Duplo | {tot_tri} RN Triplo")
        
        if st.button("🚀 Enviar Solicitação para Vendas", type="primary"):
            if empresa == "":
                st.error("O nome da Empresa é obrigatório.")
            else:
                id_unico = "G-" + datetime.now().strftime("%Y%m%d%H%M")
                mapa_str = df_editado.to_json(orient='records')
                
                nova_linha = [
                    id_unico, datetime.now().strftime("%d/%m/%Y"), empresa, contato, email, telefone, 
                    checkin.strftime("%d/%m/%Y"), checkout.strftime("%d/%m/%Y"), 
                    tot_sin, tot_dup, tot_tri, 0, 0, 0, 0, 
                    "Enviado para time de vendas", "", "", mapa_str
                ]
                aba_dados.append_row(nova_linha)
                st.success("✅ Grupo registrado! A equipe de vendas já pode definir as tarifas.")
                st.cache_resource.clear() 
    else:
        st.error("O Check-out deve ser maior que o Check-in.")

# ------------------------------------------------
# 3. Gestão de Vendas (Comercial)
# ------------------------------------------------
elif menu == "💼 Gestão de Vendas":
    st.header("💼 Tratativa e Precificação de Grupos")
    
    if df.empty:
        st.warning("Não há grupos.")
    else:
        df['Status_Clean'] = df['Status'].astype(str).str.strip().str.lower()
        df_pendentes = df[~df['Status_Clean'].isin(['confirmado', 'recusado'])]
        
        if df_pendentes.empty:
            st.success("Nenhum grupo pendente no momento!")
        else:
            opcoes = df_pendentes['ID'].astype(str) + " - " + df_pendentes['Empresa'] + " (" + df_pendentes['Status'] + ")"
            grupo_sel = st.selectbox("Escolha o Grupo:", opcoes)
            
            id_sel = grupo_sel.split(" - ")[0]
            linha_atual = df_pendentes[df_pendentes['ID'] == id_sel].iloc[0]
            
            rn_s = int(linha_atual['Total RN Single'] or 0)
            rn_d = int(linha_atual['Total RN Duplo'] or 0)
            rn_t = int(linha_atual['Total RN Triplo'] or 0)
            
            st.info(f"🏨 **Necessidade do Hotel:** {rn_s} Single | {rn_d} Duplo | {rn_t} Triplo")
            
            with st.form("form_vendas"):
                st.subheader("1. Definição de Tarifas")
                col1, col2, col3 = st.columns(3)
                with col1: t_single = st.number_input("Tarifa Single (R$)", value=float(linha_atual.get('Tarifa Single', 0) or 0))
                with col2: t_duplo = st.number_input("Tarifa Duplo (R$)", value=float(linha_atual.get('Tarifa Duplo', 0) or 0))
                with col3: t_triplo = st.number_input("Tarifa Triplo (R$)", value=float(linha_atual.get('Tarifa Triplo', 0) or 0))
                
                st.subheader("2. Ação de Vendas")
                novo_status = st.radio("Mudar status para:", ["Cotação enviada", "Confirmado", "Recusado"], horizontal=True)
                
                c_data, c_motivo = st.columns(2)
                with c_data: novo_deadline = st.date_input("Deadline (Se cotação)", value=date.today())
                with c_motivo: motivo = st.selectbox("Motivo (Se recusado)", ["", "Preço", "Estrutura", "Não informado", "Sem disponibilidade"])
                
                if st.form_submit_button("💾 Salvar e Calcular Receita", type="primary"):
                    if novo_status == "Recusado" and motivo == "":
                        st.error("⚠️ Escolha um motivo de recusa.")
                    else:
                        receita_total = (rn_s * t_single) + (rn_d * t_duplo) + (rn_t * t_triplo)
                        linha_planilha = df[df['ID'] == id_sel].index[0] + 2
                        
                        aba_dados.update_cell(linha_planilha, 12, t_single)
                        aba_dados.update_cell(linha_planilha, 13, t_duplo)
                        aba_dados.update_cell(linha_planilha, 14, t_triplo)
                        aba_dados.update_cell(linha_planilha, 15, receita_total)
                        aba_dados.update_cell(linha_planilha, 16, novo_status)
                        
                        if novo_status == "Cotação enviada":
                            aba_dados.update_cell(linha_planilha, 17, novo_deadline.strftime("%d/%m/%Y"))
                            aba_dados.update_cell(linha_planilha, 18, "")
                        elif novo_status == "Recusado":
                            aba_dados.update_cell(linha_planilha, 17, "") 
                            aba_dados.update_cell(linha_planilha, 18, motivo)
                        elif novo_status == "Confirmado":
                            aba_dados.update_cell(linha_planilha, 17, "") 
                            aba_dados.update_cell(linha_planilha, 18, "") 
                            
                        st.success(f"✅ Atualizado! Receita calculada: R$ {receita_total:,.2f}")
                        st.cache_resource.clear()

# ------------------------------------------------
# 4. Follow-up (Hotel)
# ------------------------------------------------
elif menu == "👀 Follow-up":
    st.header("👀 Acompanhamento da Operação (Hotel)")
    if df.empty:
        st.warning("Nenhum dado cadastrado.")
    else:
        t1, t2, t3 = st.tabs(["⚠️ Sem Tratativa (Vendas)", "⏳ Cotações em Aberto", "✅ Confirmados"])
        
        df['Status_Clean'] = df['Status'].astype(str).str.strip().str.lower()
        
        with t1:
            st.subheader("Aguardando Precificação / Ação da Comercial")
            df_sem_acao = df[df['Status_Clean'].str.contains("enviado", na=False)]
            
            if not df_sem_acao.empty:
                st.dataframe(df_sem_acao[['Data Envio', 'Empresa', 'Contato', 'Total RN Single', 'Total RN Duplo', 'Total RN Triplo']], use_container_width=True)
            else:
                st.info("Nenhum grupo pendente sem tratativa no momento.")
            
        with t2:
            st.subheader("Cotações Enviadas (Deadlines)")
            df_cotacoes = df[df['Status_Clean'].str.contains("cotação enviada", na=False)].copy()
            
            if not df_cotacoes.empty:
                df_cotacoes['Deadline_Date'] = pd.to_datetime(df_cotacoes['Deadline'], format='%d/%m/%Y', errors='coerce')
                hoje = pd.to_datetime(date.today())
                df_cotacoes['Situação'] = df_cotacoes['Deadline_Date'].apply(lambda x: "🔴 Atrasado" if pd.notnull(x) and x < hoje else "🟢 No Prazo")
                st.dataframe(df_cotacoes[['Empresa', 'Contato', 'Deadline', 'Situação', 'Receita Total']], use_container_width=True)
            else:
                st.info("Nenhuma cotação em aberto.")
                
        with t3:
            st.subheader("Histórico de Grupos Confirmados")
            df_conf = df[df['Status_Clean'].str.contains("confirmado", na=False)].copy()
            
            if not df_conf.empty:
                st.dataframe(df_conf[['Check-in', 'Check-out', 'Empresa', 'Receita Total']], use_container_width=True)
            else:
                st.info("Nenhum grupo confirmado ainda.")
