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
                    
                    # 1. Atualiza a aba de dados do grupo (Dados ou Vendas_Diretas)
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
                    
                    # 2. Atualiza ou cria a linha correspondente na aba Propostas (que gera o visual web do cliente)
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
                    
                    # Limpa a observação antiga de ajuste para destravar a proposta para o cliente visualizar a nova versão atualizada
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
