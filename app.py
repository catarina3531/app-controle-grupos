import streamlit as st
import pandas as pd
from datetime import date, datetime
import gspread
from google.oauth2.service_account import Credentials
import altair as alt

st.set_page_config(page_title="CRM Grupos - Hotel", page_icon="🏨", layout="wide")

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
    dados_planilha = aba_dados.get_all_records()
    df = pd.DataFrame(dados_planilha)
except Exception as e:
    st.error(f"Erro ao conectar: {e}")
    st.stop()

# ------------------------------------------------
# Menu Lateral
# ------------------------------------------------
st.sidebar.title("🏨 Menu Principal")
menu = st.sidebar.radio("Navegação:", [
    "📊 1. Dashboard Gerencial", 
    "🛎️ 2. Nova Solicitação (Hotel)", 
    "💼 3. Gestão de Vendas (Comercial)", 
    "👀 4. Follow-up (Hotel)"
])

# ------------------------------------------------
# 1. Dashboard Gerencial
# ------------------------------------------------
if menu == "📊 1. Dashboard Gerencial":
    st.header("📊 Visão Gerencial de Grupos")
    
    if df.empty:
        st.info("Nenhum dado cadastrado ainda.")
    else:
        df['Data Envio'] = pd.to_datetime(df['Data Envio'], format='%d/%m/%Y', errors='coerce')
        df['Mês/Ano'] = df['Data Envio'].dt.to_period('M').astype(str)
        
        meses_disponiveis = sorted(df['Mês/Ano'].dropna().unique().tolist(), reverse=True)
        mes_selecionado = st.selectbox("Filtrar por Mês de Entrada do Lead:", ["Todos"] + meses_disponiveis)
        
        if mes_selecionado != "Todos":
            df_dash = df[df['Mês/Ano'] == mes_selecionado]
        else:
            df_dash = df

        st.markdown("### Indicadores Principais")
        col1, col2, col3, col4 = st.columns(4)
        
        total_leads = len(df_dash)
        enviados = len(df_dash[df_dash['Status'] == 'Cotação enviada'])
        confirmados = len(df_dash[df_dash['Status'] == 'Confirmado'])
        recusados = len(df_dash[df_dash['Status'] == 'Recusado'])
        
        col1.metric("📌 Total de Leads Recebidos", total_leads)
        col2.metric("📤 Propostas Enviadas", enviados)
        col3.metric("✅ Grupos Confirmados", confirmados)
        col4.metric("❌ Grupos Recusados", recusados)
        
        st.markdown("---")
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.subheader("Funil de Status")
            status_contagem = df_dash['Status'].value_counts().reset_index()
            status_contagem.columns = ['Status', 'Quantidade']
            grafico_barras = alt.Chart(status_contagem).mark_bar(color='#4CAF50').encode(
                x='Quantidade', y=alt.Y('Status', sort='-x')
            )
            st.altair_chart(grafico_barras, use_container_width=True)
            
        with col_graf2:
            st.subheader("Motivos de Recusa")
            df_recusados = df_dash[df_dash['Status'] == 'Recusado']
            if not df_recusados.empty:
                motivos = df_recusados['Motivo Recusa'].value_counts().reset_index()
                motivos.columns = ['Motivo', 'Quantidade']
                grafico_pizza = alt.Chart(motivos).mark_arc(innerRadius=50).encode(
                    theta='Quantidade', color='Motivo', tooltip=['Motivo', 'Quantidade']
                )
                st.altair_chart(grafico_pizza, use_container_width=True)
            else:
                st.info("Nenhuma recusa neste período.")

# ------------------------------------------------
# 2. Nova Solicitação (Hotel)
# ------------------------------------------------
elif menu == "🛎️ 2. Nova Solicitação (Hotel)":
    st.header("🛎️ Enviar Grupo para Vendas")

    with st.form("form_novo_grupo", clear_on_submit=True):
        st.subheader("Dados do Cliente")
        col1, col2, col3, col4 = st.columns(4)
        with col1: empresa = st.text_input("Empresa / Agência")
        with col2: contato = st.text_input("Nome do Contato")
        with col3: email = st.text_input("E-mail")
        with col4: telefone = st.text_input("Telefone")
            
        st.subheader("Datas")
        col_in, col_out = st.columns(2)
        with col_in: checkin = st.date_input("Check-in", value=date.today())
        with col_out: checkout = st.date_input("Check-out", value=date.today())
        
        st.subheader("Necessidade de Hospedagem")
        col_s, col_d, col_t = st.columns(3)
        with col_s: 
            st.markdown("**SINGLE**")
            qtde_single = st.number_input("Qtde Single", min_value=0, step=1)
            tarifa_single = st.number_input("Tarifa Single (R$)", min_value=0.0, format="%.2f")
        with col_d: 
            st.markdown("**DUPLO**")
            qtde_duplo = st.number_input("Qtde Duplo", min_value=0, step=1)
            tarifa_duplo = st.number_input("Tarifa Duplo (R$)", min_value=0.0, format="%.2f")
        with col_t: 
            st.markdown("**TRIPLO**")
            qtde_triplo = st.number_input("Qtde Triplo", min_value=0, step=1)
            tarifa_triplo = st.number_input("Tarifa Triplo (R$)", min_value=0.0, format="%.2f")

        st.markdown("---")
        submit_btn = st.form_submit_button("🚀 Enviar Solicitação", use_container_width=True)

        if submit_btn:
            dias = (checkout - checkin).days
            if dias <= 0 or empresa == "":
                st.error("⚠️ Verifique as datas e o nome da empresa.")
            else:
                id_unico = "G-" + datetime.now().strftime("%Y%m%d%H%M%S")
                data_atual = datetime.now().strftime("%d/%m/%Y")
                
                total_rn = (qtde_single + qtde_duplo + qtde_triplo) * dias
                receita = ((qtde_single * tarifa_single) + (qtde_duplo * tarifa_duplo) + (qtde_triplo * tarifa_triplo)) * dias
                
                # Campos ordenados conf. nova planilha (Sem KAM, com Triplo)
                nova_linha = [
                    id_unico, data_atual, empresa, contato, email, telefone, 
                    checkin.strftime("%d/%m/%Y"), checkout.strftime("%d/%m/%Y"), 
                    qtde_single, tarifa_single, qtde_duplo, tarifa_duplo, qtde_triplo, tarifa_triplo,
                    dias, total_rn, receita, "Enviado para time de vendas", "", ""
                ]
                aba_dados.append_row(nova_linha)
                st.success("✅ Grupo registrado e enviado para a equipe de Vendas!")
                st.cache_resource.clear() 

# ------------------------------------------------
# 3. Gestão de Vendas (Comercial)
# ------------------------------------------------
elif menu == "💼 3. Gestão de Vendas (Comercial)":
    st.header("💼 Atualização de Status (Equipe de Vendas)")
    
    if df.empty:
        st.warning("Não há grupos cadastrados.")
    else:
        df_pendentes = df[~df['Status'].isin(['Confirmado', 'Recusado'])]
        
        if df_pendentes.empty:
            st.success("🎉 Todos os grupos foram tratados (Confirmados ou Recusados). Nenhum pendente!")
        else:
            opcoes_grupos = df_pendentes['ID'].astype(str) + " - " + df_pendentes['Empresa'] + " (" + df_pendentes['Status'] + ")"
            grupo_selecionado = st.selectbox("Escolha o Grupo", opcoes_grupos)
            
            id_selecionado = grupo_selecionado.split(" - ")[0]
            
            with st.form("form_vendas"):
                novo_status = st.radio("Mudar status para:", ["Cotação enviada", "Confirmado", "Recusado"])
                
                st.markdown("---")
                st.info("💡 Se 'Cotação enviada', defina o Deadline. Se 'Recusado', informe o Motivo.")
                novo_deadline = st.date_input("Deadline (Se cotação enviada)", value=date.today())
                motivo = st.selectbox("Motivo (Se recusado)", ["", "Preço", "Estrutura", "Não informado", "Sem disponibilidade"])
                
                salvar_status = st.form_submit_button("Salvar Atualização", type="primary", use_container_width=True)
                
                if salvar_status:
                    if novo_status == "Recusado" and motivo == "":
                        st.error("⚠️ Para recusar, você deve escolher um motivo.")
                    else:
                        linha_planilha = df[df['ID'] == id_selecionado].index[0] + 2
                        
                        # Novas colunas na planilha (Triplo adicionado, KAM removido): 
                        # 18: Status | 19: Deadline | 20: Motivo Recusa
                        aba_dados.update_cell(linha_planilha, 18, novo_status)
                        
                        if novo_status == "Cotação enviada":
                            aba_dados.update_cell(linha_planilha, 19, novo_deadline.strftime("%d/%m/%Y"))
                            aba_dados.update_cell(linha_planilha, 20, "")
                        elif novo_status == "Recusado":
                            aba_dados.update_cell(linha_planilha, 19, "") 
                            aba_dados.update_cell(linha_planilha, 20, motivo)
                        elif novo_status == "Confirmado":
                            aba_dados.update_cell(linha_planilha, 19, "") 
                            aba_dados.update_cell(linha_planilha, 20, "") 
                            
                        st.success(f"Status do grupo {id_selecionado} atualizado para {novo_status}!")
                        st.cache_resource.clear()

# ------------------------------------------------
# 4. Follow-up (Hotel)
# ------------------------------------------------
elif menu == "👀 4. Follow-up (Hotel)":
    st.header("👀 Acompanhamento da Operação (Hotel)")
    
    if df.empty:
        st.warning("Nenhum dado.")
    else:
        tab1, tab2, tab3 = st.tabs(["⚠️ Sem Tratativa (Vendas)", "⏳ Controle de Deadlines", "✅ Confirmados e Histórico"])
        
        with tab1:
            st.subheader("Enviados para Vendas, mas sem ação ainda")
            df_sem_acao = df[df['Status'] == 'Enviado para time de vendas']
            st.dataframe(df_sem_acao[['Data Envio', 'Empresa', 'Contato', 'Receita Total']], use_container_width=True)
            
        with tab2:
            st.subheader("Cotações Enviadas (Visão Deadline)")
            df_cotacoes = df[df['Status'] == 'Cotação enviada'].copy()
            
            if not df_cotacoes.empty:
                df_cotacoes['Deadline_Date'] = pd.to_datetime(df_cotacoes['Deadline'], format='%d/%m/%Y', errors='coerce')
                hoje = pd.to_datetime(date.today())
                
                df_cotacoes['Situação'] = df_cotacoes['Deadline_Date'].apply(lambda x: "🔴 Atrasado" if pd.notnull(x) and x < hoje else "🟢 No Prazo")
                
                st.dataframe(df_cotacoes[['Empresa', 'Contato', 'Deadline', 'Situação', 'Receita Total']], use_container_width=True)
            else:
                st.info("Nenhuma cotação aguardando deadline no momento.")
                
        with tab3:
            st.subheader("Histórico de Confirmados")
            df_conf = df[df['Status'] == 'Confirmado'].copy()
            
            if not df_conf.empty:
                df_conf['Ano Check-in'] = pd.to_datetime(df_conf['Check-in'], format='%d/%m/%Y', errors='coerce').dt.year.astype(str)
                filtro_ano = st.selectbox("Filtrar por Ano do Evento", ["Todos"] + sorted(df_conf['Ano Check-in'].dropna().unique().tolist(), reverse=True))
                
                if filtro_ano != "Todos":
                    df_conf = df_conf[df_conf['Ano Check-in'] == filtro_ano]
                    
                st.dataframe(df_conf[['Check-in', 'Check-out', 'Empresa', 'Total RN', 'Receita Total']], use_container_width=True)
            else:
                st.info("Nenhum grupo confirmado ainda.")
