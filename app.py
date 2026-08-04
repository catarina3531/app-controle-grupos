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
                opcoes = df_pendentes['ID'].astype(str) + " - " + df_pendentes['Empresa'] + " (" + df_pendentes['Origem_Fluxo'] + " - Status: " + df_pendentes['Status'] + ")"
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

                st.markdown("### 💰 1. Precificação (Tarifa NET)")
                c1, c2, c3 = st.columns(3)
                t_single, t_duplo, t_triplo = 0.0, 0.0, 0.0
                
                with c1:
                    if rn_s > 0: t_single = st.number_input("Tarifa Single (R$)", value=tarifa_single_salva, key=f"g_ts_{v}")
                with c2:
                    if rn_d > 0: t_duplo = st.number_input("Tarifa Duplo (R$)", value=tarifa_duplo_salva, key=f"g_td_{v}")
                with c3:
                    if rn_t > 0: t_triplo = st.number_input("Tarifa Triplo (R$)", value=tarifa_triplo_salva, key=f"g_tt_{v}")

                st.markdown("### 🏨 2. Tipologia de Apartamento")
                st.write("Selecione quais os tipos de quarto que o hotel disponibilizará (conforme as opções aplicáveis):")
                tipologias_disponiveis = obter_tipologias_compativeis(rn_s, rn_d, rn_t)
                tipologias_selecionadas = st.multiselect("Tipologias:", options=tipologias_disponiveis, key=f"g_tipo_{v}")

                st.markdown("### 🍽️ 3. Produtos e Serviços Extras")
                st.write("Adicione refeições, maleiro, diárias de salas, etc.")
                df_extras_inicial = pd.DataFrame([{"Produto/Serviço": "", "Qtd": 0, "Valor Unitário (R$)": 0.0} for _ in range(3)])
                df_extras = st.data_editor(df_extras_inicial, num_rows="dynamic", hide_index=True, key=f"g_extras_{v}", use_container_width=True)

                st.markdown("---")
                novo_status = st.radio("Status:", ["Cotação enviada", "Confirmado", "Recusado"], horizontal=True, key=f"radio_status_comercial_{v}")
                
                novo_deadline = date.today()
                if novo_status != "Recusado":
                    novo_deadline = st.date_input("Deadline", value=date.today(), key=f"input_deadline_comercial_{v}")
                
                motivos_recusa_lista = ["Preço", "Evento cancelado", "Categoria do Hotel", "Política de Pagamento", "Condições de Cancelamento", "Configuração dos Quartos", "Localização", "Sem retorno do cliente", "Outros"]
                motivo_recusa_input = ""
                if novo_status == "Recusado":
                    motivo_recusa_input = st.selectbox("Motivo da Recusa:", motivos_recusa_lista, key=f"sel_motivo_{v}")
                    if motivo_recusa_input == "Outros":
                        outro_texto = st.text_input("Especifique o motivo:", key=f"txt_outro_motivo_{v}")
                        if outro_texto: motivo_recusa_input = f"Outros: {outro_texto}"

                texto_botao = "💾 Registrar Recusa e Encerrar" if novo_status == "Recusado" else "💾 Salvar e Gerar Link da Proposta"
                
                if st.button(texto_botao, type="primary"):
                    tipologias_str = ", ".join(tipologias_selecionadas) if tipologias_selecionadas else "Conforme disponibilidade"
                    
                    tabela_html = "<h4>Hospedagem (Com ISS 5%):</h4>"
                    tabela_html += "<table><tr><th>Acomodação</th><th>Tipologia(s)</th><th>Qtd / RN</th><th>Valor Unit. NET</th><th>Subtotal (com ISS 5%)</th></tr>"
                    
                    receita_hospedagem = 0
                    if rn_s > 0 and t_single > 0:
                        sub = (rn_s * t_single) * 1.05
                        receita_hospedagem += (rn_s * t_single)
                        tabela_html += f"<tr><td>Diária Single</td><td>{tipologias_str}</td><td>{rn_s}</td><td>R$ {t_single:.2f}</td><td>R$ {sub:.2f}</td></tr>"
                    if rn_d > 0 and t_duplo > 0:
                        sub = (rn_d * t_duplo) * 1.05
                        receita_hospedagem += (rn_d * t_duplo)
                        tabela_html += f"<tr><td>Diária Dupla</td><td>{tipologias_str}</td><td>{rn_d}</td><td>R$ {t_duplo:.2f}</td><td>R$ {sub:.2f}</td></tr>"
                    if rn_t > 0 and t_triplo > 0:
                        sub = (rn_t * t_triplo) * 1.05
                        receita_hospedagem += (rn_t * t_triplo)
                        tabela_html += f"<tr><td>Diária Tripla</td><td>{tipologias_str}</td><td>{rn_t}</td><td>R$ {t_triplo:.2f}</td><td>R$ {sub:.2f}</td></tr>"
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
