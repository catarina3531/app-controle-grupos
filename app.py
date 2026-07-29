import streamlit as st
import pandas as pd
from datetime import date

# ------------------------------------------------
# 1. Configuração Inicial da Página
# ------------------------------------------------
st.set_page_config(
    page_title="Controle de Grupos - Hospedagem",
    page_icon="🏨",
    layout="wide"
)

# ------------------------------------------------
# 2. Menu de Navegação (Sidebar)
# ------------------------------------------------
st.sidebar.title("🏨 Menu Principal")
menu = st.sidebar.radio(
    "Navegação:",
    ["📊 Dashboard", "📝 Nova Solicitação", "📋 Lista de Grupos"]
)

# ------------------------------------------------
# 3. Tela: Nova Solicitação (Formulário)
# ------------------------------------------------
if menu == "📝 Nova Solicitação":
    st.header("📝 Nova Solicitação de Grupo (Hospedagem)")
    st.markdown("Preencha os dados abaixo. Os cálculos de Room Nights e Receita são automáticos.")

    with st.form("form_novo_grupo"):
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

        # Lógica de cálculo após clicar em salvar
        if submit_button:
            dias = (checkout - checkin).days
            
            if dias <= 0:
                st.error("⚠️ A data de Check-out deve ser posterior à data de Check-in.")
            elif empresa == "":
                st.warning("⚠️ O nome da Empresa/Agência é obrigatório.")
            else:
                # Cálculos Automáticos
                rn_single = qtde_single * dias
                rn_duplo = qtde_duplo * dias
                total_rn = rn_single + rn_duplo
                
                receita_single = rn_single * tarifa_single
                receita_duplo = rn_duplo * tarifa_duplo
                receita_total = receita_single + receita_duplo
                
                st.success(f"✅ Solicitação processada com sucesso!")
                
                # Exibindo o resumo dos cálculos na tela
                st.info(f"""
                **Resumo da Cotação:**
                * **Duração:** {dias} noites
                * **Total de Room Nights (RN):** {total_rn}
                * **Receita Prevista (Hospedagem):** R$ {receita_total:,.2f}
                """)
                
                # TODO: Aqui entrará o código futuro para enviar esses dados para o Google Sheets

# ------------------------------------------------
# 4. Tela: Dashboard (Visão Geral)
# ------------------------------------------------
elif menu == "📊 Dashboard":
    st.header("📊 Dashboard de Desempenho")
    
    # Criando métricas falsas (mock data) para visualização do layout
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Propostas Mês", "12", "3")
    col2.metric("Room Nights Bloqueadas", "450", "15%")
    col3.metric("Receita Confirmada", "R$ 125.000", "R$ 15.000")
    col4.metric("Taxa de Conversão", "45%", "-5%")

    st.markdown("---")
    st.subheader("Últimas Cotações Inseridas")
    
    # Tabela simulada
    dados_mock = pd.DataFrame({
        "Proposta": ["001", "002", "003"],
        "Empresa": ["Bayer", "Totvs", "Itaú"],
        "Status": ["Confirmada", "Enviada", "Cotação"],
        "Check-in": ["15/08/2026", "22/09/2026", "05/10/2026"],
        "RN Total": [120, 80, 200],
        "Receita (R$)": [45000, 28000, 75000]
    })
    st.dataframe(dados_mock, use_container_width=True)

# ------------------------------------------------
# 5. Tela: Lista de Grupos
# ------------------------------------------------
elif menu == "📋 Lista de Grupos":
    st.header("📋 Lista Completa de Grupos")
    st.info("Esta tela será conectada ao Google Sheets para exibir e permitir a edição de todo o histórico de hospedagens de 2026.")
