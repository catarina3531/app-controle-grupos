import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

# ------------------------------------------------
# 1. Configuração Inicial e Conexão com Google
# ------------------------------------------------
st.set_page_config(page_title="Controle de Grupos - Hospedagem", page_icon="🏨", layout="wide")

# Link real da sua planilha
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1_vvU_tgDtHCqtoKG4xR5XMfmnujGTXf7pndgg_aQoX0/edit?gid=0#gid=0" 

@st.cache_resource
def conectar_planilha():
    # Puxa a senha segura que salvamos no Secrets do Streamlit
    credenciais = dict(st.secrets["gcp_service_account"])
    escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    creds = Credentials.from_service_account_info(credenciais, scopes=escopos)
    cliente = gspread.authorize(creds)
    
    # Abre a planilha pelo link
    planilha = cliente.open_by_url(URL_PLANILHA).sheet1
    return planilha

# Tenta conectar. Se der erro, avisa na tela.
try:
    aba_dados = conectar_planilha()
except Exception as e:
    st.error(f"Erro ao conectar com o Google Sheets: {e}")
    st.stop()

# ------------------------------------------------
# 2. Menu de Navegação (Sidebar)
# ------------------------------------------------
st.sidebar.title("🏨 Menu Principal")
menu = st.sidebar.radio("Navegação:", ["📝 Nova Solicitação", "📋 Lista de Grupos"])

# ------------------------------------------------
# 3. Tela: Nova Solicitação (Formulário)
# ------------------------------------------------
if menu == "📝 Nova Solicitação":
    st.header("📝 Nova Solicitação de Grupo (Hospedagem)")
    st.markdown("Preencha os dados abaixo para salvar direto no Google Sheets.")

    with st.form("form_novo_grupo", clear_on_submit=True):
        st.subheader("1. Dados do Cliente")
        col1, col2, col3 = st.columns(3)
        with col1:
            empresa = st.text_input("Empresa / Agência")
            contato = st.text_input("Nome do Contato")
        with col2:
            email = st.text_input("E-mail")
            telefone = st.text_input("Telefone")
        with col3:
            kam = st.selectbox("KAM Responsável", ["Selecione", "Danillo", "Maria", "João"])
            status = st.selectbox("Status", ["Cotação", "Enviada", "Bloqueada", "Confirmada", "Cancelada"])

        st.subheader("2. Datas do Evento")
        col4, col5 = st.columns(2)
        with col4:
            checkin = st.date_input("Data de Check-in", value=date.today())
        with col5:
            checkout = st.date_input("Data de Check-out", value=date.today())

        st.subheader("3. Detalhes de Hospedagem")
        col6, col7, col8, col9 = st.columns(4)
        with col6:
            qtde_single = st.number_input("Qtde Aptos Single", min_value=0, step=1)
        with col7:
            tarifa_single = st.number_input("Tarifa Single (R$)", min_value=0.0, step=10.0, format="%.2f")
        with col8:
            qtde_duplo = st.number_input("Qtde Aptos Duplo", min_value=0, step=1)
        with col9:
            tarifa_duplo = st.number_input("Tarifa Duplo (R$)", min_value=0.0, step=10.0, format="%.2f")

        st.markdown("---")
        submit_button = st.form_submit_button(label="💾 Salvar Solicitação", use_container_width=True)

        # Ação ao clicar no botão de salvar
        if submit_button:
            dias = (checkout - checkin).days
            
            if dias <= 0:
                st.error("⚠️ A data de Check-out deve ser posterior à data de Check-in.")
            elif empresa == "":
                st.warning("⚠️ O nome da Empresa/Agência é obrigatório.")
            else:
                rn_single = qtde_single * dias
                rn_duplo = qtde_duplo * dias
                total_rn = rn_single + rn_duplo
                receita_total = (rn_single * tarifa_single) + (rn_duplo * tarifa_duplo)
                
                # Monta a linha com os dados na exata ordem das colunas da planilha
                nova_linha = [
                    empresa, contato, email, telefone, kam, status, 
                    checkin.strftime("%d/%m/%Y"), checkout.strftime("%d/%m/%Y"), 
                    qtde_single, tarifa_single, qtde_duplo, tarifa_duplo, 
                    dias, total_rn, receita_total
                ]
                
                # Envia para o Google Sheets
                aba_dados.append_row(nova_linha)
                
                st.success(f"✅ Solicitação salva com sucesso na planilha!")
                st.info(f"**Resumo:** {dias} noites | {total_rn} RNs | Receita: R$ {receita_total:,.2f}")

# ------------------------------------------------
# 4. Tela: Lista de Grupos
# ------------------------------------------------
elif menu == "📋 Lista de Grupos":
    st.header("📋 Lista Completa de Grupos")
    st.markdown("Dados puxados diretamente da sua planilha:")
    
    # Busca os dados da planilha e transforma em uma tabela (DataFrame)
    try:
        dados = aba_dados.get_all_records()
        if len(dados) > 0:
            df = pd.DataFrame(dados)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("A planilha ainda está vazia. Preencha uma nova solicitação!")
    except Exception as e:
        st.error(f"Erro ao carregar a lista: A primeira linha da planilha não tem os cabeçalhos. Verifique as colunas na linha 1 do Google Sheets. Erro técnico: {e}")
