# ------------------------------------------------
# 4. Follow-up (Hotel)
# ------------------------------------------------
elif menu == "👀 Follow-up":
    st.header("👀 Acompanhamento da Operação (Hotel)")
    if df.empty:
        st.warning("Nenhum dado cadastrado.")
    else:
        t1, t2, t3 = st.tabs(["⚠️ Sem Tratativa (Vendas)", "⏳ Cotações em Aberto", "✅ Confirmados"])
        
        # Padroniza os textos de status para evitar conflitos de busca
        df['Status_Clean'] = df['Status'].astype(str).str.strip().str.lower()
        
        with t1:
            st.subheader("Aguardando Precificação / Ação da Comercial")
            # Busca flexível por qualquer lead que contenha "enviado"
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
