import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import altair as alt
import json

st.set_page_config(page_title="CRM Grupos & Propostas", page_icon="🏨", layout="wide")

# 🌟 Estilo CSS para o efeito de piscar nos alertas
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
    </style>
""", unsafe_allow_html=True)

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1_vvU_tgDtHCqtoKG4xR5XMfmnujGTXf7pndgg_aQoX0/edit?gid=0#gid=0"
URL_WEB_APP = "https://script.google.com/macros/s/AKfycbz7vQ65GWPeo1_qJpngvHkYG3G_GMmo_XYdsT-RSzcMisSHz70rtik3ftANwA3KGme1SQ/exec"

@st.cache_resource(ttl=30) 
def conectar_planilhas():
    credenciais = dict(st.secrets["gcp_service_account"])
    escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(credenciais, scopes=escopos)
    cliente = gspread.authorize(creds)
    
    planilha = cliente.open_by_url(URL_PLANILHA)
    aba_dados = planilha.worksheet("Dados")
    aba_usuarios = planilha.worksheet("Usuarios")
    
    try:
        aba_propostas = planilha.worksheet("Propostas")
    except:
        aba_propostas = planilha.add_worksheet(title="Propostas", rows=100, cols=10)
        aba_propostas.append_row(['ID_Proposta', 'Cliente', 'Email', 'Produtos_Contratados', 'Valor_Total', 'Status', 'Observacoes', 'Data_Criacao', 'Ultimo_Acesso'])

    try:
        aba_produtos = planilha.worksheet("Produtos")
    except:
        aba_produtos = planilha.add_worksheet(title="Produtos", rows=50, cols=3)
        aba_produtos.append_row(['ID', 'Produto', 'Valor_Padrao'])

    return aba_dados, aba_usuarios, aba_propostas, aba_produtos

try:
    aba_dados, aba_usuarios, aba_propostas, aba_produtos = conectar_planilhas()
    
    dados_planilha = aba_dados.get_all_records(expected_headers=[
        'ID', 'Data Envio', 'Empresa', 'Contato', 'E-mail', 'Telefone', 
        'Check-in', 'Check-out', 'Total RN Single', 'Total RN Duplo', 'Total RN Triplo', 
        'Tarifa Single', 'Tarifa Duplo', 'Tarifa Triplo', 'Receita Total', 
        'Status', 'Deadline', 'Motivo Recusa', 'Mapa de Quartos'
    ])
    df = pd.DataFrame(dados_planilha)
    if not df.empty:
        df.columns = df.columns.str.strip()
        
    todos_valores_user = aba_usuarios.get_all_values()
    if len(todos_valores_user) <= 1:
        if len(todos_valores_user) == 0:
            aba_usuarios.append_row(['Usuario', 'Senha', 'Perfil', 'Primeiro Acesso'])
            
        usuarios_iniciais = [
            ["Amanda", "mudar@123", "Hotel", "Sim"],
            ["Italo", "mudar@123", "Hotel", "Sim"],
            ["Amanda Rolim", "mudar@123", "Vendas", "Sim"],
            ["Rafaella", "mudar@123", "Vendas", "Sim"],
            ["Elton", "mudar@123", "Vendas", "Sim"],
            ["Catarina", "mudar@123", "Gerencial", "Sim"],
            ["Kessia", "mudar@123", "Gerencial", "Sim"],
            ["Cecilia", "mudar@123", "Gerencial", "Sim"],
        ]
        for u in usuarios_iniciais:
            aba_usuarios.append_row(u)
        todos_valores_user = aba_usuarios.get_all_values()

    header = todos_valores_user[0]
    rows = todos_valores_user[1:]
    df_usuarios = pd.DataFrame(rows, columns=header)
    df_usuarios.columns = df_usuarios.columns.str.strip()
            
except Exception as e:
    st.error(f"Erro ao conectar com as abas do Google Sheets: {e}")
    st.stop()

# ------------------------------------------------
# Sistema de Login e Troca de Senha Obrigatória
# ------------------------------------------------
if "logado" not in st.session_state:
    st.session_state["logado"] = False
    st.session_state["usuario"] = ""
    st.session_state["perfil"] = ""
    st.session_state["mudar_senha"] = False

if not st.session_state["logado"]:
    st.title("🔐 Acesso ao Sistema de Grupos")
    
    lista_usuarios_validos = df_usuarios['Usuario'].dropna().tolist()
    usuario_input = st.selectbox("Selecione seu Nome de Usuário", [""] + lista_usuarios_validos)
    senha_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar", type="primary"):
        if usuario_input == "":
            st.warning("Selecione um usuário.")
        else:
            user_row = df_usuarios[df_usuarios['Usuario'] == usuario_input].iloc[0]
            senha_cadastrada = str(user_row['Senha']).strip()
            
            if senha_input == senha_cadastrada:
                st.session_state["logado"] = True
                st.session_state["usuario"] = usuario_input
                st.session_state["perfil"] = str(user_row['Perfil']).strip()
                
                if str(user_row['Primeiro Acesso']).strip() == "Sim" or senha_cadastrada == "mudar@123":
                    st.session_state["mudar_senha"] = True
                st.rerun()
            else:
                st.error("Senha incorreta!")
    st.stop()

if st.session_state["mudar_senha"]:
    st.title("🔑 Redefinição de Senha Obrigatória")
    st.warning("Detectamos que você está usando uma senha padrão ou temporária. Por favor, crie sua nova senha pessoal para continuar.")
    
    with st.form("form_nova_senha"):
        nova_senha1 = st.text_input("Nova Senha", type="password")
        nova_senha2 = st.text_input("Confirme a Nova Senha", type="password")
        btn_trocar = st.form_submit_button("Salvar Nova Senha", type="primary")
        
        if btn_trocar:
            if nova_senha1 == "" or nova_senha1 != nova_senha2:
                st.error("As senhas não coincidem ou estão em branco.")
            elif nova_senha1 == "mudar@123":
                st.error("Escolha uma senha diferente da padrão.")
            else:
                idx = df_usuarios[df_usuarios['Usuario'] == st.session_state["usuario"]].index[0] + 2
                aba_usuarios.update_cell(idx, 2, nova_senha1) 
                aba_usuarios.update_cell(idx, 4, "Não") 
                
                st.success("Senha alterada com sucesso! Entrando no sistema...")
                st.session_state["mudar_senha"] = False
                st.cache_resource.clear()
                st.rerun()
    st.stop()

st.sidebar.button("Sair (Logout)", on_click=lambda: st.session_state.clear())

# ------------------------------------------------
# Alertas Automáticos com Efeito Piscando
# ------------------------------------------------
if not df.empty:
    df['Status_Clean'] = df['Status'].astype(str).str.strip().str.lower()
    hoje = pd.to_datetime(date.today())
    
    df_cot_atrasadas = df[df['Status_Clean'].str.contains("cotação enviada", na=False)].copy()
    if not df_cot_atrasadas.empty:
        df_cot_atrasadas['Deadline_Dt'] = pd.to_datetime(df_cot_atrasadas['Deadline'], format='%d/%m/%Y', errors='coerce')
        atrasados = df_cot_atrasadas[df_cot_atrasadas['Deadline_Dt'] < hoje]
        if len(atrasados) > 0:
            st.markdown(f'<div class="alerta-piscando">🚨 ATENÇÃO: Existem <b>{len(atrasados)}</b> cotações com o DEADLINE VENCIDO!</div>', unsafe_allow_html=True)

    df_sem_tratativa = df[df['Status_Clean'].str.contains("enviado", na=False)].copy()
    if not df_sem_tratativa.empty:
        df_sem_tratativa['Envio_Dt'] = pd.to_datetime(df_sem_tratativa['Data Envio'], format='%d/%m/%Y', errors='coerce')
        
        def conta_dias_uteis(data_envio):
            if pd.isnull(data_envio): return 0
            dias_uteis = 0
            atual = data_envio.date()
            fim = date.today()
            while atual < fim:
                atual += timedelta(days=1)
                if atual.weekday() < 5: 
                    dias_uteis += 1
            return dias_uteis

        df_sem_tratativa['Dias_Uteis_Atraso'] = df_sem_tratativa['Envio_Dt'].apply(conta_dias_uteis)
        atraso_vendas = df_sem_tratativa[df_sem_tratativa['Dias_Uteis_Atraso'] > 2]
        
        if len(atraso_vendas) > 0:
            st.markdown(f'<div class="alerta-piscando">⚠️ AVISO OPERACIONAL: Há <b>{len(atraso_vendas)}</b> solicitações SEM TRATATIVA há mais de 2 dias úteis!</div>', unsafe_allow_html=True)

# ------------------------------------------------
# Menu Lateral por Perfil
# ------------------------------------------------
perfil = st.session_state["perfil"]
usuario_atual = st.session_state["usuario"]
st.sidebar.title(f"🏨 Olá, {usuario_atual}")
st.sidebar.caption(f"Perfil: {perfil}")

opcoes_menu = []
if perfil == "Gerencial":
    opcoes_menu = ["📊 Dashboard", "🛎️ Nova Solicitação", "💼 Gestão de Vendas & Propostas", "👀 Follow-up", "⚙️ Gerenciar Usuários"]
elif perfil == "Hotel":
    opcoes_menu = ["🛎️ Nova Solicitação", "👀 Follow-up"]
elif perfil == "Vendas":
    opcoes_menu = ["📊 Dashboard", "💼 Gestão de Vendas & Propostas", "👀 Follow-up"]

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
        df['Mês/Ano Envio'] = df['Data Envio'].dt.to_period('M').astype(str)
        
        meses_disponiveis = sorted(df['Mês/Ano Envio'].dropna().unique().tolist(), reverse=True)
        mes_selecionado = st.selectbox("Filtrar por Mês de Entrada (Criação do Lead):", ["Todos"] + meses_disponiveis)
        
        df_dash = df[df['Mês/Ano Envio'] == mes_selecionado] if mes_selecionado != "Todos" else df

        st.subheader("📌 Indicadores por Mês de Solicitação")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Leads Recebidos", len(df_dash))
        col2.metric("Propostas Enviadas", len(df_dash[df_dash['Status_Clean'].str.contains("cotação enviada", na=False)]))
        col3.metric("Confirmados", len(df_dash[df_dash['Status_Clean'].str.contains("confirmado", na=False)]))
        col4.metric("Recusados", len(df_dash[df_dash['Status_Clean'].str.contains("recusado", na=False)]))
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Funil de Status (Mês selecionado)")
            status_contagem = df_dash['Status'].value_counts().reset_index()
            status_contagem.columns = ['Status', 'Quantidade']
            grafico_barras = alt.Chart(status_contagem).mark_bar(color='#4CAF50').encode(x='Quantidade', y=alt.Y('Status', sort='-x'))
            st.altair_chart(grafico_barras, use_container_width=True)
            
        with c2:
            st.subheader("Motivos de Recusa")
            df_recusados = df_dash[df_dash['Status_Clean'].str.contains("recusado", na=False)]
            if not df_recusados.empty:
                motivos = df_recusados['Motivo Recusa'].value_counts().reset_index()
                motivos.columns = ['Motivo', 'Quantidade']
                grafico_pizza = alt.Chart(motivos).mark_arc(innerRadius=50).encode(theta='Quantidade', color='Motivo', tooltip=['Motivo', 'Quantidade'])
                st.altair_chart(grafico_pizza, use_container_width=True)
            else:
                st.info("Nenhuma recusa neste período.")

        st.markdown("---")
        st.header("📈 Impacto na Ocupação (Por Mês de Check-in)")
        df_confirmados = df[df['Status_Clean'].str.contains("confirmado", na=False)].copy()
        if not df_confirmados.empty:
            df_confirmados['Checkin_Dt'] = pd.to_datetime(df_confirmados['Check-in'], format='%d/%m/%Y', errors='coerce')
            df_confirmados['Mes_Checkin'] = df_confirmados['Checkin_Dt'].dt.to_period('M').astype(str)
            
            resumo_checkin = df_confirmados.groupby('Mes_Checkin').agg(
                Qtd_Grupos=('ID', 'count'),
                Total_RN_Single=('Total RN Single', lambda x: pd.to_numeric(x, errors='coerce').sum()),
                Total_RN_Duplo=('Total RN Duplo', lambda x: pd.to_numeric(x, errors='coerce').sum()),
                Total_RN_Triplo=('Total RN Triplo', lambda x: pd.to_numeric(x, errors='coerce').sum()),
                Receita_Prevista=('Receita Total', lambda x: pd.to_numeric(x, errors='coerce').sum())
            ).reset_index()
            
            resumo_checkin['Total_RN_Geral'] = resumo_checkin['Total_RN_Single'] + resumo_checkin['Total_RN_Duplo'] + resumo_checkin['Total_RN_Triplo']
            resumo_checkin = resumo_checkin.sort_values('Mes_Checkin', ascending=False)
            
            st.dataframe(
                resumo_checkin.rename(columns={
                    'Mes_Checkin': 'Mês de Check-in',
                    'Qtd_Grupos': 'Qtd. Grupos',
                    'Total_RN_Single': 'RN Single',
                    'Total_RN_Duplo': 'RN Duplo',
                    'Total_RN_Triplo': 'RN Triplo',
                    'Total_RN_Geral': 'Total RNs',
                    'Receita_Prevista': 'Receita Prevista (R$)'
                }), 
                hide_index=True, 
                use_container_width=True
            )
            
            grafico_impacto = alt.Chart(resumo_checkin).mark_bar(color='#2196F3').encode(
                x=alt.X('Mes_Checkin:N', title='Mês de Check-in', sort='ascending'),
                y=alt.Y('Receita_Prevista:Q', title='Receita Prevista (R$)'),
                tooltip=['Mes_Checkin', 'Qtd_Grupos', 'Total_RN_Geral', 'Receita_Prevista']
            ).properties(title="Receita Confirmada por Mês de Hospedagem")
            st.altair_chart(grafico_impacto, use_container_width=True)
        else:
            st.info("Ainda não há grupos confirmados para calcular o impacto na ocupação.")

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
                st.success("✅ Grupo registrado! A equipe de vendas já pode definir as tarifas e emitir a proposta.")
                st.cache_resource.clear() 
    else:
        st.error("O Check-out deve ser maior que o Check-in.")

# ------------------------------------------------
# 3. Gestão de Vendas & Emissão de Proposta (Unificado com Tipologias)
# ------------------------------------------------
elif menu == "💼 Gestão de Vendas & Propostas":
    st.header("💼 Tratativa, Precificação e Envio de Proposta")
    
    if perfil not in ["Vendas", "Gerencial"]:
        st.error("🔒 **Acesso Restrito!** Apenas colaboradores da **Equipe de Vendas** podem precificar e emitir propostas comerciais.")
    else:
        if df.empty:
            st.warning("Não há grupos cadastrados.")
        else:
            df_pendentes = df[~df['Status_Clean'].isin(['confirmado', 'recusado'])]
            
            if df_pendentes.empty:
                st.success("Nenhum grupo pendente no momento!")
            else:
                opcoes = df_pendentes['ID'].astype(str) + " - " + df_pendentes['Empresa'] + " (" + df_pendentes['Status'] + ")"
                grupo_sel = st.selectbox("Escolha o Grupo para tratar:", opcoes)
                
                id_sel = grupo_sel.split(" - ")[0]
                linha_atual = df_pendentes[df_pendentes['ID'] == id_sel].iloc[0]
                
                st.markdown("---")
                st.subheader(f"📋 Informações da Solicitação: {linha_atual['Empresa']}")
                c_info1, c_info2 = st.columns(2)
                with c_info1:
                    st.markdown(f"**Contato:** {linha_atual['Contato']}")
                    st.markdown(f"**E-mail:** {linha_atual['E-mail']}")
                    st.markdown(f"**Telefone:** {linha_atual['Telefone']}")
                with c_info2:
                    st.markdown(f"**Data de Envio:** {linha_atual['Data Envio']}")
                    st.markdown(f"**Período:** {linha_atual['Check-in']} até {linha_atual['Check-out']}")
                
                mapa_json = linha_atual.get('Mapa de Quartos', '')
                if mapa_json:
                    try:
                        mapa_lista = json.loads(mapa_json)
                        df_mapa = pd.DataFrame(mapa_lista)
                        st.markdown("**📅 Distribuição Diária de Quartos solicitada pelo Hotel:**")
                        st.dataframe(df_mapa, hide_index=True, use_container_width=True)
                    except:
                        pass
                st.markdown("---")

                rn_s = int(linha_atual['Total RN Single'] or 0)
                rn_d = int(linha_atual['Total RN Duplo'] or 0)
                rn_t = int(linha_atual['Total RN Triplo'] or 0)
                
                with st.form("form_tratativa_completa"):
                    st.subheader("1. Definição de Tarifas de Hospedagem (NET)")
                    col1, col2, col3 = st.columns(3)
                    with col1: t_single = st.number_input("Tarifa Single (R$)", value=float(linha_atual.get('Tarifa Single', 0) or 0))
                    with col2: t_duplo = st.number_input("Tarifa Duplo (R$)", value=float(linha_atual.get('Tarifa Duplo', 0) or 0))
                    with col3: t_triplo = st.number_input("Tarifa Triplo (R$)", value=float(linha_atual.get('Tarifa Triplo', 0) or 0))
                    
                    st.markdown("---")
                    st.subheader("2. Tipologias e Categorias Disponíveis para o Grupo")
                    st.markdown("Selecione quais tipologias/configurações estarão disponíveis e serão exibidas na proposta:")
                    
                    tipologias_opcoes = [
                        "DBD/Standard – 01 cama de casal (01 a 02 pessoas)",
                        "DBC/Standard – 01 cama de casal e 01 cama de solteiro (01 a 03 pessoas)",
                        "TWC/Standard – 02 camas de solteiro (01 a 02 pessoas)",
                        "ROH/Superior – 01 cama de casal (01 a 02 pessoas)",
                        "S2D/Superior – 01 cama de casal e 01 cama de solteiro (01 a 03 pessoas)"
                    ]
                    
                    tipologias_selecionadas = st.multiselect("Tipologias de Apartamentos Oferecidas:", tipologias_opcoes)

                    st.markdown("---")
                    st.subheader("3. Produtos Extras & Serviços (Catering e Opcionais)")
                    
                    extras_opcoes = [
                        "Café da manhã",
                        "Almoço Buffet",
                        "Jantar Buffet",
                        "Almoço Três tempos",
                        "Jantar Três tempos",
                        "Abertura de Porta",
                        "Late Check-out",
                        "Guarda Volumes"
                    ]
                    
                    extras_selecionados = st.multiselect("Selecione itens adicionais:", extras_opcoes)
                    
                    extras_dados = []
                    if extras_selecionados:
                        st.markdown("*(Defina a quantidade e o valor unitário para os extras)*")
                        for ext in extras_selecionados:
                            ec1, ec2, ec3 = st.columns([3, 1, 1])
                            with ec1: st.write(f"**{ext}**")
                            with ec2: q_ext = st.number_input(f"Qtd ({ext})", min_value=1, value=1, key=f"q_{ext}")
                            with ec3: v_ext = st.number_input(f"Valor Unit. R$ ({ext})", min_value=0.0, value=50.0, step=5.0, key=f"v_{ext}")
                            extras_dados.append({"Item": ext, "Qtd": q_ext, "Valor": v_ext, "Subtotal": q_ext * v_ext})

                    st.markdown("---")
                    st.subheader("4. Ação Comercial e Status")
                    novo_status = st.radio("Mudar status para:", ["Cotação enviada", "Confirmado", "Recusado"], horizontal=True)
                    
                    c_data, c_motivo = st.columns(2)
                    with c_data: novo_deadline = st.date_input("Deadline (Se cotação)", value=date.today())
                    with c_motivo: motivo = st.selectbox("Motivo (Se recusado)", ["", "Preço", "Estrutura", "Não informado", "Sem disponibilidade"])
                    
                    btn_salvar = st.form_submit_button("💾 Salvar Tratativa e Gerar Link da Proposta", type="primary")
                    
                    if btn_salvar:
                        if novo_status == "Recusado" and motivo == "":
                            st.error("⚠️ Escolha um motivo de recusa.")
                        else:
                            receita_hospedagem = (rn_s * t_single) + (rn_d * t_duplo) + (rn_t * t_triplo)
                            receita_extras = sum([item["Subtotal"] for item in extras_dados])
                            receita_total = receita_hospedagem + receita_extras
                            
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
                            
                            # Monta o resumo estruturado para a Proposta
                            resumo_partes = []
                            if tipologias_selecionadas:
                                resumo_partes.append("--- TIPOLOGIAS OFERECIDAS ---")
                                for tip in tipologias_selecionadas:
                                    resumo_partes.append(f"• {tip}")
                            
                            resumo_partes.append("--- TARIFAS DE HOSPEDAGEM ---")
                            if rn_s > 0: resumo_partes.append(f"{rn_s}x Diária Single (R$ {t_single:.2f})")
                            if rn_d > 0: resumo_partes.append(f"{rn_d}x Diária Dupla (R$ {t_duplo:.2f})")
                            if rn_t > 0: resumo_partes.append(f"{rn_t}x Diária Tripla (R$ {t_triplo:.2f})")
                            
                            if extras_dados:
                                resumo_partes.append("--- PRODUTOS EXTRAS & SERVIÇOS ---")
                                for ex in extras_dados:
                                    resumo_partes.append(f"{ex['Qtd']}x {ex['Item']} (R$ {ex['Subtotal']:.2f})")
                            
                            resumo_str = " | ".join(resumo_partes)
                            id_prop = f"PROP-{id_sel}"
                            
                            aba_propostas.append_row([
                                id_prop, linha_atual['Empresa'], linha_atual['E-mail'], resumo_str, 
                                receita_total, novo_status, "", datetime.now().strftime("%d/%m/%Y"), ""
                            ])
                            
                            st.success(f"✅ Tratativa salva! Receita Total: R$ {receita_total:,.2f}")
                            
                            link_rastreavel = f"{URL_WEB_APP}?id={id_prop}&nome={linha_atual['Empresa'].replace(' ', '%20')}"
                            st.markdown("### 🔗 Link Inteligente da Proposta Gerado:")
                            st.code(link_rastreavel)
                            st.cache_resource.clear()

# ------------------------------------------------
# 4. Follow-up
# ------------------------------------------------
elif menu == "👀 Follow-up":
    st.header("👀 Acompanhamento da Operação")
    if df.empty:
        st.warning("Nenhum dado cadastrado.")
    else:
        t1, t2, t3 = st.tabs(["⚠️ Sem Tratativa", "⏳ Cotações em Aberto", "✅ Confirmados"])
        
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
            st.subheader("🗓️ Grupos Confirmados por Mês/Ano de Check-in")
            df_conf = df[df['Status_Clean'].str.contains("confirmado", na=False)].copy()
            
            if not df_conf.empty:
                df_conf['Checkin_Date'] = pd.to_datetime(df_conf['Check-in'], format='%d/%m/%Y', errors='coerce')
                df_conf['Mes_Ano'] = df_conf['Checkin_Date'].dt.to_period('M').astype(str)
                
                meses_confirmados = sorted(df_conf['Mes_Ano'].dropna().unique().tolist())
                
                if meses_confirmados:
                    filtro_mes = st.selectbox("Selecione o Mês do Check-in:", ["Todos os Meses"] + meses_confirmados)
                    
                    if filtro_mes != "Todos os Meses":
                        df_conf_filtrado = df_conf[df_conf['Mes_Ano'] == filtro_mes]
                    else:
                        df_conf_filtrado = df_conf
                        
                    st.dataframe(df_conf_filtrado[['Check-in', 'Check-out', 'Empresa', 'Total RN Single', 'Total RN Duplo', 'Total RN Triplo', 'Receita Total']], use_container_width=True)
                else:
                    st.info("Não há datas de check-in válidas nos grupos confirmados.")
            else:
                st.info("Nenhum grupo confirmado ainda.")

# ------------------------------------------------
# 5. Gerenciar Usuários (Apenas Gerencial)
# ------------------------------------------------
elif menu == "⚙️ Gerenciar Usuários" and perfil == "Gerencial":
    st.header("⚙️ Painel de Controle de Usuários")
    
    aba_user_tab1, aba_user_tab2 = st.tabs(["📋 Lista e Redefinição de Senha", "➕ Cadastrar / Excluir Usuário"])
    
    with aba_user_tab1:
        st.subheader("Usuários Ativos no Sistema")
        st.dataframe(df_usuarios[['Usuario', 'Perfil', 'Primeiro Acesso']], use_container_width=True)
        
        st.markdown("---")
        st.subheader("Redefinir Senha para Padrão (mudar@123)")
        usuario_escolhido = st.selectbox("Selecione o usuário:", df_usuarios['Usuario'].tolist())
        
        if st.button("🔄 Resetar Senha", type="primary"):
            idx_u = df_usuarios[df_usuarios['Usuario'] == usuario_escolhido].index[0] + 2
            aba_usuarios.update_cell(idx_u, 2, "mudar@123")
            aba_usuarios.update_cell(idx_u, 4, "Sim") 
            st.success(f"Senha do usuário **{usuario_escolhido}** redefinida para `mudar@123`!")
            st.cache_resource.clear()

    with aba_user_tab2:
        st.subheader("Adicionar Novo Usuário")
        with st.form("form_novo_usuario"):
            novo_nome = st.text_input("Nome do Usuário")
            novo_perfil = st.selectbox("Perfil de Acesso", ["Hotel", "Vendas", "Gerencial"])
            btn_criar = st.form_submit_button("Criar Usuário", type="primary")
            
            if btn_criar:
                if novo_nome == "":
                    st.error("O nome do usuário não pode estar em branco.")
                elif novo_nome in df_usuarios['Usuario'].values:
                    st.error("Já existe um usuário com esse nome.")
                else:
                    aba_usuarios.append_row([novo_nome, "mudar@123", novo_perfil, "Sim"])
                    st.success(f"Usuário **{novo_nome}** criado com sucesso! A senha inicial é `mudar@123`.")
                    st.cache_resource.clear()

        st.markdown("---")
        st.subheader("Excluir Usuário")
        usuario_excluir = st.selectbox("Selecione o usuário para remover:", df_usuarios['Usuario'].tolist(), key="del_user")
        
        if st.button("🗑️ Excluir Usuário", type="secondary"):
            if len(df_usuarios) <= 1:
                st.error("Você não pode excluir o último usuário restante.")
            else:
                idx_del = df_usuarios[df_usuarios['Usuario'] == usuario_excluir].index[0] + 2
                aba_usuarios.delete_rows(idx_del)
                st.success(f"Usuário **{usuario_excluir}** excluído com sucesso!")
                st.cache_resource.clear()
