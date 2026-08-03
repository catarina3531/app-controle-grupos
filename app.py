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
    </style>
""", unsafe_allow_html=True)

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1_vvU_tgDtHCqtoKG4xR5XMfmnujGTXf7pndgg_aQoX0/edit?gid=0#gid=0"
URL_WEB_APP = "https://script.google.com/macros/s/AKfycbz7vQ65GWPeo1_qJpngvHkYG3G_GMmo_XYdsT-RSzcMisSHz70rtik3ftANwA3KGme1SQ/exec"

@st.cache_resource(ttl=10) 
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
        aba_propostas = planilha.add_worksheet(title="Propostas", rows=100, cols=14)
        aba_propostas.append_row(['ID_Proposta', 'Cliente', 'Email', 'Produtos_Contratados', 'Valor_Total', 'Status', 'Observacoes', 'Data_Criacao', 'Ultimo_Acesso', 'Nome_Usuario', 'Cargo_Usuario', 'Email_Usuario', 'Tel_Usuario', 'Link_Proposta'])

    return aba_dados, aba_usuarios, aba_propostas

try:
    aba_dados, aba_usuarios, aba_propostas = conectar_planilhas()
    
    dados_planilha = aba_dados.get_all_records(expected_headers=[
        'ID', 'Data Envio', 'Empresa', 'Contato', 'E-mail', 'Telefone', 
        'Check-in', 'Check-out', 'Total RN Single', 'Total RN Duplo', 'Total RN Triplo', 
        'Tarifa Single', 'Tarifa Duplo', 'Tarifa Triplo', 'Receita Total', 
        'Status', 'Deadline', 'Motivo Recusa', 'Mapa de Quartos'
    ])
    df = pd.DataFrame(dados_planilha)
    if not df.empty:
        df.columns = df.columns.str.strip()
        
    propostas_valores = aba_propostas.get_all_values()
    if len(propostas_valores) > 1:
        header_prop = [h.strip() for h in propostas_valores[0]]
        df_propostas = pd.DataFrame(propostas_valores[1:], columns=header_prop)
    else:
        df_propostas = pd.DataFrame(columns=['ID_Proposta', 'Cliente', 'Email', 'Produtos_Contratados', 'Valor_Total', 'Status', 'Observacoes', 'Data_Criacao', 'Ultimo_Acesso', 'Link_Proposta'])

    todos_valores_user = aba_usuarios.get_all_values()
    if len(todos_valores_user) <= 1:
        if len(todos_valores_user) == 0:
            aba_usuarios.append_row(['Usuario', 'Senha', 'Perfil', 'Primeiro Acesso', 'Cargo', 'Email', 'Telefone'])
            
        usuarios_iniciais = [
            ["Amanda", "mudar@123", "Hotel", "Sim", "Analista de Distribuição e Reservas", "amanda@accor.com", "(11) 5085-5699"],
            ["Italo", "mudar@123", "Hotel", "Sim", "Analista de Distribuição e Reservas", "italo@accor.com", "(11) 5085-5699"],
            ["Amanda Ferrari", "mudar@123", "Vendas", "Sim", "Gerente de Vendas – Região Paulista & Jardins", "amanda.ferrari@accor.com", "(11) 99487-5023"],
            ["Elton", "mudar@123", "Vendas", "Sim", "Gerente de Contas / Account Manager", "elton.santos@accor.com", "(11) 94537-3303"],
            ["Catarina", "mudar@123", "Gerencial", "Não", "Gerente Geral", "catarina.costa@accor.com", "(11) 5085-5699"],
            ["Kessia", "mudar@123", "Gerencial", "Sim", "Subgerente", "kessia.gomes@accor.com", "(11) 5085-5699"],
            ["Cecilia", "mudar@123", "Gerencial", "Sim", "Coordenadora Operacional", "cecilia.maria@accor.com", "(11) 5085-5699"],
            ["Amanda Rolim", "mudar@123", "Hotel", "Sim", "Revenue Manager", "amanda.rolim@accor.com", "(11) 5085-5699"],
            ["Lucas Cardoso", "mudar@123", "Hotel", "Sim", "Supervisor de Guest Relation", "lucas.cardoso@accor.com", "(11) 5085-5699"]
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
                st.rerun()
    st.stop()

st.sidebar.button("Sair (Logout)", on_click=lambda: st.session_state.clear())

perfil = st.session_state["perfil"]
usuario_atual = st.session_state["usuario"]
st.sidebar.title(f"🏨 Olá, {usuario_atual}")
st.sidebar.caption(f"Perfil: {perfil}")

opcoes_menu = []
if perfil == "Gerencial":
    opcoes_menu = ["📊 Dashboard", "🛎️ Nova Solicitação", "💼 Gestão de Vendas & Propostas", "📑 Acompanhamento de Propostas", "👀 Follow-up", "⚙️ Gerenciar Usuários"]
elif perfil == "Hotel":
    opcoes_menu = ["🛎️ Nova Solicitação", "👀 Follow-up"]
elif perfil == "Vendas":
    opcoes_menu = ["📊 Dashboard", "💼 Gestão de Vendas & Propostas", "📑 Acompanhamento de Propostas", "👀 Follow-up"]

menu = st.sidebar.radio("Navegação:", opcoes_menu)

# 1. Dashboard
if menu == "📊 Dashboard":
    st.header("📊 Visão Gerencial de Grupos")
    if df.empty:
        st.info("Nenhum dado cadastrado.")
    else:
        df['Data Envio'] = pd.to_datetime(df['Data Envio'], format='%d/%m/%Y', errors='coerce')
        df['Mês/Ano Envio'] = df['Data Envio'].dt.to_period('M').astype(str)
        meses_disponiveis = sorted(df['Mês/Ano Envio'].dropna().unique().tolist(), reverse=True)
        mes_selecionado = st.selectbox("Filtrar por Mês de Entrada:", ["Todos"] + meses_disponiveis)
        df_dash = df[df['Mês/Ano Envio'] == mes_selecionado] if mes_selecionado != "Todos" else df

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Leads Recebidos", len(df_dash))
        col2.metric("Propostas Enviadas", len(df_dash[df_dash['Status'].str.contains("cotação enviada", case=False, na=False)]))
        col3.metric("Confirmados", len(df_dash[df_dash['Status'].str.contains("confirmado", case=False, na=False)]))
        col4.metric("Recusados", len(df_dash[df_dash['Status'].str.contains("recusado", case=False, na=False)]))

# 2. Nova Solicitação
elif menu == "🛎️ Nova Solicitação":
    st.header("🛎️ Enviar Grupo para Vendas")
    empresa = st.text_input("Empresa / Agência")
    col1, col2, col3 = st.columns(3)
    with col1: contato = st.text_input("Contato")
    with col2: email = st.text_input("E-mail")
    with col3: telefone = st.text_input("Telefone")
        
    col_in, col_out = st.columns(2)
    with col_in: checkin = st.date_input("Primeiro Check-in", value=date.today())
    with col_out: checkout = st.date_input("Último Check-out", value=date.today() + timedelta(days=1))
    
    dias = (checkout - checkin).days
    if dias > 0:
        datas_lista = [checkin + timedelta(days=i) for i in range(dias)]
        df_grid = pd.DataFrame({"Data": [d.strftime("%d/%m/%Y") for d in datas_lista], "Single": [0]*dias, "Duplo": [0]*dias, "Triplo": [0]*dias})
        df_editado = st.data_editor(df_grid, hide_index=True, use_container_width=True)
        
        if st.button("🚀 Enviar Solicitação para Vendas", type="primary"):
            if empresa == "":
                st.error("O nome da Empresa é obrigatório.")
            else:
                id_unico = "G-" + datetime.now().strftime("%Y%m%d%H%M")
                nova_linha = [
                    id_unico, datetime.now().strftime("%d/%m/%Y"), empresa, contato, email, telefone, 
                    checkin.strftime("%d/%m/%Y"), checkout.strftime("%d/%m/%Y"), 
                    int(df_editado["Single"].sum()), int(df_editado["Duplo"].sum()), int(df_editado["Triplo"].sum()), 
                    0, 0, 0, 0, "Enviado para time de vendas", "", "", df_editado.to_json(orient='records')
                ]
                aba_dados.append_row(nova_linha)
                st.success("✅ Grupo registrado com sucesso!")
                st.cache_resource.clear()

# 3. Gestão de Vendas & Proposta
elif menu == "💼 Gestão de Vendas & Propostas":
    st.header("💼 Tratativa, Precificação e Envio de Proposta")
    if perfil not in ["Vendas", "Gerencial"]:
        st.error("🔒 Acesso Restrito!")
    else:
        if df.empty:
            st.warning("Nenhum grupo cadastrado.")
        else:
            df['Status_Clean'] = df['Status'].astype(str).str.strip().str.lower()
            df_pendentes = df[~df['Status_Clean'].isin(['confirmado', 'recusado'])]
            
            if df_pendentes.empty:
                st.success("Nenhum grupo pendente no momento!")
            else:
                opcoes = df_pendentes['ID'].astype(str) + " - " + df_pendentes['Empresa'] + " (" + df_pendentes['Status'] + ")"
                grupo_sel = st.selectbox("Escolha o Grupo para tratar:", opcoes)
                id_sel = grupo_sel.split(" - ")[0]
                linha_atual = df_pendentes[df_pendentes['ID'] == id_sel].iloc[0]
                
                rn_s = int(linha_atual['Total RN Single'] or 0)
                rn_d = int(linha_atual['Total RN Duplo'] or 0)
                rn_t = int(linha_atual['Total RN Triplo'] or 0)
                
                st.subheader("1. Tarifas de Hospedagem (NET)")
                c1, c2, c3 = st.columns(3)
                t_single, t_duplo, t_triplo = 0.0, 0.0, 0.0
                
                with c1:
                    if rn_s > 0:
                        t_single = st.number_input("Tarifa Single (R$)", value=float(linha_atual.get('Tarifa Single', 0) or 0))
                    else:
                        st.info("Single: Não solicitado")
                with c2:
                    if rn_d > 0:
                        t_duplo = st.number_input("Tarifa Duplo (R$)", value=float(linha_atual.get('Tarifa Duplo', 0) or 0))
                    else:
                        st.info("Duplo: Não solicitado")
                with c3:
                    if rn_t > 0:
                        t_triplo = st.number_input("Tarifa Triplo (R$)", value=float(linha_atual.get('Tarifa Triplo', 0) or 0))
                    else:
                        st.info("Triplo: Não solicitado")
                
                st.subheader("2. Tipologias Oferecidas")
                tipologias_disponiveis = []
                if rn_s > 0:
                    tipologias_disponiveis.extend([
                        "DBD/Standard – 01 cama de casal (01 a 02 pessoas - Single)",
                        "TWC/Standard – 02 camas de solteiro (01 a 02 pessoas - Single)",
                        "ROH/Superior – 01 cama de casal (01 a 02 pessoas - Single)"
                    ])
                if rn_d > 0:
                    tipologias_disponiveis.extend([
                        "DBD/Standard – 01 cama de casal (01 a 02 pessoas - Duplo)",
                        "TWC/Standard – 02 camas de solteiro (01 a 02 pessoas - Duplo)",
                        "ROH/Superior – 01 cama de casal (01 a 02 pessoas - Duplo)"
                    ])
                if rn_t > 0:
                    tipologias_disponiveis.extend([
                        "DBC/Standard – 01 cama de casal e 01 cama de solteiro (01 a 03 pessoas - Triplo)",
                        "S2D/Superior – 01 cama de casal e 01 cama de solteiro (01 a 03 pessoas - Triplo)"
                    ])
                
                tipologias_selecionadas = st.multiselect("Tipologias de Apartamentos Disponíveis:", tipologias_disponiveis)

                st.subheader("3. Produtos Extras & Serviços")
                extras_opcoes = ["Almoço Buffet", "Jantar Buffet", "Almoço Três tempos", "Jantar Três tempos", "Abertura de Porta", "Late Check-out", "Guarda Volumes"]
                extras_selecionados = st.multiselect("Selecione adicionais:", extras_opcoes)
                
                extras_dados = []
                if extras_selecionados:
                    st.markdown("Preencha os valores para os itens selecionados:")
                    for ext in extras_selecionados:
                        ec1, ec2, ec3 = st.columns([3, 1, 1])
                        with ec1: st.write(f"**{ext}**")
                        with ec2: q_ext = st.number_input(f"Qtd ({ext})", min_value=1, value=1, key=f"q_{ext}")
                        with ec3: v_ext = st.number_input(f"Valor Unit. R$ ({ext})", min_value=0.0, value=50.0, step=5.0, key=f"v_{ext}")
                        extras_dados.append({"Item": ext, "Qtd": q_ext, "Valor": v_ext, "Subtotal": q_ext * v_ext})

                st.subheader("4. Descrição Livre / Cardápio / Observações")
                descricao_livre = st.text_area("Insira aqui detalhes do cardápio ou observações específicas que aparecerão na proposta:", placeholder="Ex: Almoço executivo composto por entrada, prato principal e sobremesa...")

                st.subheader("5. Status Comercial")
                novo_status = st.radio("Status:", ["Cotação enviada", "Confirmado", "Recusado"], horizontal=True)
                novo_deadline = st.date_input("Deadline", value=date.today())
                
                if st.button("💾 Salvar e Gerar Link da Proposta", type="primary"):
                    receita_hospedagem = (rn_s * t_single) + (rn_d * t_duplo) + (rn_t * t_triplo)
                    receita_extras = sum([item["Subtotal"] for item in extras_dados])
                    receita_total = receita_hospedagem + receita_extras
                    
                    linha_planilha = df[df['ID'] == id_sel].index[0] + 2
                    aba_dados.update_cell(linha_planilha, 12, t_single)
                    aba_dados.update_cell(linha_planilha, 13, t_duplo)
                    aba_dados.update_cell(linha_planilha, 14, t_triplo)
                    aba_dados.update_cell(linha_planilha, 15, receita_total)
                    aba_dados.update_cell(linha_planilha, 16, novo_status)
                    aba_dados.update_cell(linha_planilha, 17, novo_deadline.strftime("%d/%m/%Y") if novo_status == "Cotação enviada" else "")
                    
                    tabela_html = ""
                    if tipologias_selecionadas:
                        tabela_html += "<h4>Tipologias de Apartamentos Oferecidas:</h4><ul>"
                        for tp in tipologias_selecionadas:
                            tabela_html += f"<li><b>{tp}</b></li>"
                        tabela_html += "</ul><br>"

                    tabela_html += "<h4>Discriminação de Valores (Com ISS 5%):</h4>"
                    tabela_html += "<table><tr><th>Serviço / Acomodação</th><th>Qtd / RN</th><th>Valor Unit. NET</th><th>Subtotal (com ISS 5%)</th></tr>"
                    
                    if rn_s > 0 and t_single > 0: 
                        tabela_html += f"<tr><td>Diária Single</td><td>{rn_s}</td><td>R$ {t_single:.2f}</td><td>R$ {(rn_s * t_single * 1.05):.2f}</td></tr>"
                    if rn_d > 0 and t_duplo > 0: 
                        tabela_html += f"<tr><td>Diária Dupla</td><td>{rn_d}</td><td>R$ {t_duplo:.2f}</td><td>R$ {(rn_d * t_duplo * 1.05):.2f}</td></tr>"
                    if rn_t > 0 and t_triplo > 0: 
                        tabela_html += f"<tr><td>Diária Tripla</td><td>{rn_t}</td><td>R$ {t_triplo:.2f}</td><td>R$ {(rn_t * t_triplo * 1.05):.2f}</td></tr>"
                    
                    for ex in extras_dados:
                        tabela_html += f"<tr><td>{ex['Item']}</td><td>{ex['Qtd']}</td><td>R$ {ex['Valor']:.2f}</td><td>R$ {ex['Subtotal']:.2f}</td></tr>"
                    tabela_html += "</table>"

                    if descricao_livre.strip():
                        tabela_html += f"<br><h4>Observações / Cardápio:</h4><p>{descricao_livre.replace(chr(10), '<br>')}</p>"
                    
                    id_prop = f"PROP-{id_sel}"
                    data_hj = datetime.now().strftime("%d/%m/%Y")
                    link_rastreavel = f"{URL_WEB_APP}?id={id_prop}&nome={linha_atual['Empresa'].replace(' ', '%20')}"
                    
                    u_logado = st.session_state.get("usuario", "Equipe")
                    u_cargo = st.session_state.get("cargo", "Gerente Geral")
                    u_email = st.session_state.get("email_user", "catarina.costa@accor.com")
                    u_tel = st.session_state.get("tel_user", "(11) 5085-5699")

                    propostas_atuais = aba_propostas.get_all_values()
                    achou = False
                    for idx_p, p_row in enumerate(propostas_atuais[1:], start=2):
                        if p_row[0] == id_prop:
                            aba_propostas.update(f'A{idx_p}:N{idx_p}', [[
                                id_prop, linha_atual['Empresa'], linha_atual['E-mail'], tabela_html, 
                                f"{receita_total * 1.05:,.2f}", novo_status, "", data_hj, "",
                                u_logado, u_cargo, u_email, u_tel, link_rastreavel
                            ]])
                            achou = True
                            break
                    
                    if not achou:
                        aba_propostas.append_row([
                            id_prop, linha_atual['Empresa'], linha_atual['E-mail'], tabela_html, 
                            f"{receita_total * 1.05:,.2f}", novo_status, "", data_hj, "",
                            u_logado, u_cargo, u_email, u_tel, link_rastreavel
                        ])
                    
                    st.success(f"✅ Proposta gerada/atualizada com sucesso! Valor Total com ISS: R$ {(receita_total * 1.05):,.2f}")
                    st.markdown("### 🔗 Link Inteligente para Envio:")
                    st.code(link_rastreavel)
                    st.cache_resource.clear()

# 4. Acompanhamento de Propostas (Garante o link mesmo para propostas antigas)
elif menu == "📑 Acompanhamento de Propostas":
    st.header("📑 Acompanhamento e Reenvio de Propostas")
    if df_propostas.empty:
        st.info("Nenhuma proposta registrada até o momento.")
    else:
        df_propostas['Data_Dt'] = pd.to_datetime(df_propostas['Data_Criacao'], format='%d/%m/%Y', errors='coerce')
        df_propostas['Mês/Ano'] = df_propostas['Data_Dt'].dt.to_period('M').astype(str)
        
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            meses_disponiveis = sorted(df_propostas['Mês/Ano'].dropna().unique().tolist(), reverse=True)
            filtro_mes = st.selectbox("Filtrar por Mês/Ano de Criação:", ["Todos"] + meses_disponiveis)
        with c_f2:
            filtro_status = st.selectbox("Filtrar por Status da Proposta:", ["Todas", "Pendente", "Aceita pelo Cliente", "Em Ajuste / Solicitação", "Recusada"])
        
        df_exib = df_propostas.copy()
        if filtro_mes != "Todos":
            df_exib = df_exib[df_exib['Mês/Ano'] == filtro_mes]
        if filtro_status != "Todas":
            df_exib = df_exib[df_exib['Status'] == filtro_status]
        
        if df_exib.empty:
            st.warning("Nenhuma proposta encontrada com os filtros selecionados.")
        else:
            st.markdown(f"Exibindo **{len(df_exib)}** proposta(s):")
            for idx, row in df_exib.iterrows():
                id_p = row.get('ID_Proposta', '')
                cliente_p = row.get('Cliente', 'Cliente')
                
                # Reconstrói o link automaticamente se a coluna estiver em branco ou indisponível
                link_proposta = row.get('Link_Proposta', '')
                if not link_proposta or str(link_proposta).strip() == "" or str(link_proposta).lower() == "nan":
                    link_proposta = f"{URL_WEB_APP}?id={id_p}&nome={str(cliente_p).replace(' ', '%20')}"
                
                with st.expander(f"📌 {cliente_p} (ID: {id_p}) - Status: **{row.get('Status', '')}**"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**E-mail:** {row.get('Email', '')}")
                        st.write(f"**Valor Total:** R$ {row.get('Valor_Total', '0.00')}")
                        st.write(f"**Data de Criação:** {row.get('Data_Criacao', '')}")
                    with col_b:
                        st.write(f"**Último Acesso do Cliente:** {row.get('Ultimo_Acesso', 'Nunca acessada')}")
                        st.write(f"**Ajustes Solicitados:** {row.get('Observacoes', 'Nenhum ajuste pendente')}")
                    
                    st.markdown("**Link da Proposta (Copie para reenviar):**")
                    st.code(link_proposta)

# 5. Follow-up
elif menu == "👀 Follow-up":
    st.header("👀 Acompanhamento da Operação")
    if df.empty:
        st.warning("Nenhum dado cadastrado.")
    else:
        t1, t2, t3 = st.tabs(["⚠️ Sem Tratativa", "⏳ Cotações em Aberto", "✅ Confirmados"])
        with t1:
            st.dataframe(df[df['Status_Clean'].str.contains("enviado", na=False)][['Data Envio', 'Empresa', 'Contato']], use_container_width=True)
        with t2:
            st.dataframe(df[df['Status_Clean'].str.contains("cotação enviada", na=False)][['Empresa', 'Deadline', 'Receita Total']], use_container_width=True)
        with t3:
            st.dataframe(df[df['Status_Clean'].str.contains("confirmado", na=False)][['Check-in', 'Check-out', 'Empresa', 'Receita Total']], use_container_width=True)

# 6. Gerenciar Usuários
elif menu == "⚙️ Gerenciar Usuários" and perfil == "Gerencial":
    st.header("⚙️ Painel de Controle de Usuários")
    tab_u1, tab_u2 = st.tabs(["📋 Usuários Cadastrados", "➕ Adicionar / Editar Perfil"])
    with tab_u1:
        colunas_publicas = [c for c in df_usuarios.columns if c.lower() != 'senha']
        st.dataframe(df_usuarios[colunas_publicas], use_container_width=True)
    with tab_u2:
        st.subheader("Cadastrar Novo Usuário ou Atualizar Perfil")
        with st.form("form_cad_usuario"):
            u_nome = st.text_input("Nome do Usuário")
            u_senha = st.text_input("Senha Inicial", value="mudar@123", type="password")
            u_perfil = st.selectbox("Perfil de Acesso", ["Hotel", "Vendas", "Gerencial"])
            u_cargo = st.text_input("Cargo / Função (Ex: Gerente Geral)", value="Gerente Geral")
            u_email = st.text_input("E-mail Corporativo", value="catarina.costa@accor.com")
            u_tel = st.text_input("Telefone / Contato", value="(11) 5085-5699")
            
            btn_salvar_user = st.form_submit_button("Salvar Usuário", type="primary")
            if btn_salvar_user:
                if not u_nome:
                    st.error("O nome do usuário é obrigatório.")
                else:
                    aba_usuarios.append_row([u_nome, u_senha, u_perfil, "Sim", u_cargo, u_email, u_tel])
                    st.success(f"✅ Usuário **{u_nome}** cadastrado com sucesso!")
                    st.cache_resource.clear()
