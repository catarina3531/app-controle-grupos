const SEU_EMAIL = "catarina.costa@accor.com";

function doGet(e) {
  const idProposta = e.parameter.id;
  const nomeCliente = e.parameter.nome;
  const acao = e.parameter.acao;
  const ajusteTexto = e.parameter.ajusteTexto || "";
  
  if (!idProposta) return HtmlService.createHtmlOutput("Proposta não encontrada.");

  const planilha = SpreadsheetApp.getActiveSpreadsheet();
  const sheetPropostas = planilha.getSheetByName("Propostas");
  
  if (!sheetPropostas) return HtmlService.createHtmlOutput("Erro: Aba 'Propostas' não encontrada.");

  const dados = sheetPropostas.getDataRange().getValues();
  let linhaProposta = -1;
  let resumoProdutos = "";
  let valorTotal = "0.00";
  let dataCriacao = "";
  let nomeUsuario = "Equipe Comercial";
  let cargoUsuario = "Gerente Geral";
  let emailUsuario = "catarina.costa@accor.com";
  let telUsuario = "(11) 5085-5699";

  for (let i = 1; i < dados.length; i++) {
    if (dados[i][0] == idProposta) {
      linhaProposta = i + 1;
      resumoProdutos = dados[i][3];
      valorTotal = dados[i][4];
      dataCriacao = dados[i][7] || new Date().toLocaleDateString('pt-BR');
      
      // Puxa da aba Propostas (Colunas J, K, L, M)
      if (dados[i].length > 9 && dados[i][9]) nomeUsuario = dados[i][9];
      if (dados[i].length > 10 && dados[i][10]) cargoUsuario = dados[i][10];
      if (dados[i].length > 11 && dados[i][11]) emailUsuario = dados[i][11];
      if (dados[i].length > 12 && dados[i][12]) telUsuario = dados[i][12];
      break;
    }
  }

  if (linhaProposta == -1) return HtmlService.createHtmlOutput("Proposta não localizada.");

  // TRATAMENTO DE AÇÃO (Aceitar, Ajuste ou Recusar)
  if (acao) {
    let novoStatus = "";
    let assuntoEmail = "";
    let mensagemDetalhe = "";
    
    if (acao === "aceitar") {
      novoStatus = "Aceita pelo Cliente";
      assuntoEmail = `🎉 Sucesso! O cliente ${nomeCliente} ACEITOU a proposta!`;
      mensagemDetalhe = "O cliente aceitou os termos da proposta.";
    } else if (acao === "ajuste") {
      novoStatus = "Em Ajuste / Solicitação";
      assuntoEmail = `🔄 Atenção: O cliente ${nomeCliente} solicitou AJUSTES na proposta!`;
      mensagemDetalhe = `Observação do cliente:\n"${ajusteTexto}"`;
      sheetPropostas.getRange(linhaProposta, 7).setValue(ajusteTexto);
    } else if (acao === "recusardireto") {
      novoStatus = "Recusada";
      assuntoEmail = `❌ Aviso: O cliente ${nomeCliente} RECUSOU a proposta.`;
      mensagemDetalhe = "O cliente recusou a proposta.";
    }

    sheetPropostas.getRange(linhaProposta, 6).setValue(novoStatus);

    try {
      MailApp.sendEmail(
        emailUsuario,
        assuntoEmail,
        `Olá ${nomeUsuario},\n\nO cliente ${nomeCliente} (Proposta ID: ${idProposta}) respondeu à proposta.\n\nStatus: ${novoStatus}\n${mensagemDetalhe}\n\nResumo:\n${resumoProdutos}\n\nValor Total: R$ ${valorTotal}`
      );
    } catch(err) {}

    return HtmlService.createHtmlOutput(`
      <html>
        <head><meta charset="utf-8">
        <style>body { font-family: Arial; background: #f4f6f9; text-align: center; padding: 50px; }</style>
        </head>
        <body>
          <div style="max-width: 500px; background: #fff; padding: 40px; border-radius: 8px; margin: auto; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #00703c;">🏨 Ibis Budget São Paulo Paraíso</h2>
            <p>Obrigado, <b>${nomeCliente}</b>!</p>
            <p>Sua resposta foi enviada com sucesso ao hotel. Nossa equipe entrará em contato em breve.</p>
          </div>
        </body>
      </html>
    `);
  }

  // RASTREAMENTO DE LEITURA (PRIMEIRO ACESSO)
  if (!e.parameter.lido) {
    sheetPropostas.getRange(linhaProposta, 9).setValue(new Date());
    try {
      MailApp.sendEmail(
        emailUsuario,
        `👀 Alerta: O cliente ${nomeCliente} abriu a proposta!`,
        `Olá ${nomeUsuario},\n\nO cliente ${nomeCliente} (Proposta ID: ${idProposta}) acabou de abrir a proposta.\n\nResumo:\n${resumoProdutos}\n\nValor Total: R$ ${valorTotal}`
      );
    } catch(err) {}
  }

  const scriptUrl = ScriptApp.getService().getUrl();
  let contemAlimentos = resumoProdutos.toLowerCase().includes("almoço") || resumoProdutos.toLowerCase().includes("jantar") || resumoProdutos.toLowerCase().includes("café da manhã");

  // TELA DA CARTA ACORDO OFICIAL FORMATADA
  return HtmlService.createHtmlOutput(`
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { font-family: Arial, sans-serif; background-color: #f4f6f9; color: #333; padding: 20px; line-height: 1.6; }
          .container { max-width: 800px; background: #fff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin: auto; }
          .header { text-align: center; border-bottom: 2px solid #00703c; padding-bottom: 20px; margin-bottom: 20px; }
          .logo { max-width: 160px; height: auto; margin-bottom: 10px; }
          .hotel-nome { font-size: 20px; font-weight: bold; color: #00703c; text-transform: uppercase; }
          .data-envio { text-align: right; font-weight: bold; color: #555; margin-bottom: 20px; }
          h3 { color: #00703c; border-bottom: 1px solid #ddd; padding-bottom: 5px; margin-top: 30px; }
          .produtos { background: #f9f9f9; padding: 20px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #00703c; }
          .destaque { background: #fff3cd; border: 1px solid #ffeeba; padding: 12px; border-radius: 5px; font-weight: bold; color: #856404; text-align: center; margin: 20px 0; }
          table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 14px; }
          th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
          th { background-color: #f2f2f2; color: #333; }
          .valor-total { font-size: 20px; font-weight: bold; color: #00703c; text-align: right; margin: 20px 0; }
          .botoes { margin-top: 30px; display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
          .btn { padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; color: white; border: none; cursor: pointer; font-size: 14px; display: inline-block; }
          .btn-aceitar { background-color: #28a745; }
          .btn-ajuste { background-color: #ffc107; color: #333; }
          .btn-recusar { background-color: #dc3545; }
          .box-ajuste { display: none; background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 15px; border: 1px solid #ffeeba; }
          textarea { width: 100%; height: 80px; padding: 8px; border-radius: 4px; border: 1px solid #ccc; margin-top: 5px; font-family: Arial; box-sizing: border-box; }
          .assinatura { margin-top: 40px; border-top: 1px solid #ddd; padding-top: 15px; font-size: 14px; color: #444; }
        </style>
        <script>
          function mostrarCampoAjuste() {
            document.getElementById('bloco-ajuste').style.display = 'block';
          }
          function enviarAjuste(event) {
            event.preventDefault();
            var texto = document.getElementById('textoAjuste').value;
            if(!texto.trim()) {
              alert('Por favor, descreva o ajuste desejado.');
              return;
            }
            var url = "${scriptUrl}?id=${idProposta}&nome=${encodeURIComponent(nomeCliente)}&acao=ajuste&lido=1&ajusteTexto=" + encodeURIComponent(texto);
            document.body.innerHTML = "<div style='text-align:center; padding:50px; font-family:Arial;'><h2>Enviando solicitação ao hotel...</h2></div>";
            fetch(url).then(function() {
              document.body.innerHTML = "<div style='max-width:500px; background:#fff; padding:40px; border-radius:8px; margin:50px auto; text-align:center; font-family:Arial; box-shadow:0 4px 10px rgba(0,0,0,0.1);'><h2 style='color:#00703c;'>🏨 Ibis Budget São Paulo Paraíso</h2><p>Obrigado, <b>${nomeCliente}</b>!</p><p>Sua solicitação de ajuste foi enviada com sucesso ao hotel.</p></div>";
            });
          }
        </script>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <img src="https://group-accor.imgix.net/https%3A%2F%2Fimages.group.accor.com%2Fyrj0orc8tx24%2F6ot5rWSoRzhfUhNSoPpSf9%2F932ab95914d753fac2e5510b11cdee2e%2FLogoMarque-Groupe_ibis-budget.svg?ixlib=js-3.8.0&w=480&q=80&auto=format&fit=crop&crop=focalpoint&s=96a349e61a8d5e512cc52df7642ed09f" class="logo" alt="Logo Ibis Budget">
            <div class="hotel-nome">Ibis Budget São Paulo Paraíso</div>
          </div>
          
          <div class="data-envio">
            São Paulo, ${dataCriacao}
          </div>
          
          <p>Prezado(a) <b>${nomeCliente}</b>,</p>
          <p>Agradecemos pelo contato e interesse de se acomodar no Ibis Budget São Paulo Paraíso. Segue nossa proposta para sua avaliação:</p>
          
          <h3>PRAZO E STATUS DA CARTA ACORDO</h3>
          <p>
            • Esta proposta é válida exclusivamente para o período descrito, com prazo de vigência de 10 dias corridos.<br>
            • No momento, não há bloqueio de apartamentos; a disponibilidade está sujeita à ocupação do hotel.<br>
            • Os valores apresentados são aplicáveis mediante a confirmação de todos os serviços descritos nesta proposta. Qualquer alteração ou redução nos serviços contratados poderá implicar em reajuste nos valores.<br>
            • Para confirmação das hospedagens, solicitamos que o pedido de bloqueio dos apartamentos e/ou demais serviços seja formalizado por e-mail.
          </p>
          
          <h3>HOSPEDAGEM</h3>
          <div class="produtos">
            ${resumoProdutos}
          </div>

          <div class="destaque">
            ⚠️ PARA VALORES DE HOSPEDAGENS PARA UM NÚMERO INFERIOR DE 10 APARTAMENTOS, FAVOR CONSULTAR DIRETAMENTE EM NOSSO SITE: ALL.COM
          </div>

          <p>
            <b>Categorias de apartamentos nas seguintes configurações:</b><br>
            • <b>DBD/Standard</b> – 01 cama de casal (01 a 02 pessoas)<br>
            • <b>DBC/Standard</b> – 01 cama de casal e 01 cama de solteiro (01 a 03 pessoas)<br>
            • <b>TWC/Standard</b> – 02 camas de solteiro (01 a 02 pessoas)<br>
            • <b>ROH/Superior</b> – 01 cama de casal (01 a 02 pessoas)<br>
            • <b>S2D/Superior</b> – 01 cama de casal e 01 cama de solteiro (01 a 03 pessoas)
          </p>

          <p>
            • Café da manhã incluso na diária, servido no restaurante:<br>
            &nbsp;&nbsp;&nbsp;&nbsp;- Segunda à sexta: das 06H30 às 10H00 da manhã.<br>
            &nbsp;&nbsp;&nbsp;&nbsp;- Sábado, Domingo e feriados: das 07H00 às 11H00 da manhã.<br>
            • Sobre as diárias, incide taxa de 5% de Imposto sobre Serviço (ISS), conforme detalhado na planilha acima.<br>
            • Tarifas de hospedagem NET, não comissionada; OU Tarifas de hospedagem comissionadas em R$ 10 por reserva / diária (após o check-out).<br>
            • O hotel oferece internet cortesia aos hóspedes, com acesso disponível nos apartamentos, áreas comuns e de lazer.<br>
            • O contrato é válido exclusivamente para as categorias e configurações de apartamento informadas.<br>
            • O estacionamento não está incluído na proposta. O pagamento deve ser realizado diretamente pelo hóspede à empresa responsável pelo serviço de valet/estacionamento.
          </p>

          ${contemAlimentos ? `
            <h3>ALIMENTOS E BEBIDAS</h3>
            <p>
              • Para sua segurança o hotel não permite a entrada ou saída de alimentos no restaurante.<br>
              • Valores abaixo como sugestão para as hospedagens. Após a carta acordo assinada, os serviços abaixo mencionados serão considerados como contratados e garantidos de forma integral ao bloqueio e contrato.<br>
              • Os valores de alimentos & bebidas são NET, não comissionados.
            </p>
          ` : ''}

          <div class="valor-total">
            Valor Total Geral: R$ ${valorTotal}
          </div>

          <h3>OBSERVAÇÕES GERAIS</h3>
          <p>
            • <b>Horários de Check-in e Check-out:</b> O check-in está disponível a partir das 15h00 e o check-out deve ser realizado até às 12h00.<br>
            • <b>Early Check-in:</b> Para garantir a entrada antecipada no apartamento, recomendamos a reserva da noite anterior à chegada. Nesse caso, será cobrada a diária integral como pré-registro.<br>
            • <b>Late Check-out:</b> Para check-out realizado entre 12h00 e 13h00, será cobrada meia diária mediante a disponibilidade. Após esse horário, será aplicada a cobrança de uma diária completa (pós-registro).<br>
            • <b>Guarda bagagens:</b> O hotel dispõe de guarda-volumes por durante 24h, com custo adicional. Consultar valores diretamente com a equipe de reservas do hotel.<br>
            • <b>Rooming List (Lista de Hóspedes):</b> A lista com os nomes dos hóspedes deverá ser enviada com, no mínimo, 10 dias de antecedência da data de entrada, contendo: nome, sobrenome, categoria do apartamento, data de entrada e saída. Em casos de duplos ou triplos, indicar a divisão de hóspedes.<br>
            • <b>Política de Crianças:</b> Bebês de 0 a 2 anos, berço como cortesia (sujeito à disponibilidade). Crianças de 2 a 11 anos hospedagem gratuita no mesmo apartamento dos pais utilizando a mesma cama.<br>
            • <b>Menores de 18 anos:</b> Menores desacompanhados devem apresentar autorização com firma reconhecida dos pais/responsáveis e documento de identidade.
          </p>

          <h3>CONDIÇÕES DE PAGAMENTO</h3>
          <p>
            O pagamento pode ser realizado 100% antecipadamente, através de cartão de crédito e depósito bancário.<br><br>
            <b>Formas de Pagamento:</b><br>
            • <b>Cartão de Crédito:</b> Solicitar previamente a carta de autorização de débito ou link para pagamento online (Aceitamos todas as bandeiras exceto HIPERCARD. Cheques não são aceitos).<br>
            • <b>PIX:</b> Utilizar o CNPJ do hotel informado no contrato e enviar o comprovante por e-mail.<br>
            • <b>Depósito Bancário:</b> Obrigatória a apresentação do comprovante enviado por e-mail diretamente ao hotel.
          </p>

          <h3>AGENDA DE PAGAMENTOS</h3>
          <table>
            <tr><th>Data</th><th>Valor a ser pago</th></tr>
            <tr><td>05 dias após a assinatura da carta acordo</td><td>20% do total da carta</td></tr>
            <tr><td>59 dias da data do evento</td><td>30% do total da carta</td></tr>
            <tr><td>39 dias da data do evento</td><td>30% do total da carta</td></tr>
            <tr><td>20 dias da data do evento</td><td>20% do total da carta</td></tr>
          </table>

          <h3>CONDIÇÕES DE CANCELAMENTO</h3>
          <p>Em caso de cancelamento, alteração de data ou redução no número de diárias, serão aplicadas as seguintes taxas sobre o valor total do contrato:</p>
          <table>
            <tr><th>Anterior à data prevista</th><th>Taxa a ser cobrada</th></tr>
            <tr><td>Da confirmação até 60 dias antes do evento</td><td>20% do total da carta</td></tr>
            <tr><td>Entre 59 e 40 dias</td><td>50% do total da carta</td></tr>
            <tr><td>Entre 39 e 20 dias</td><td>80% do total da carta</td></tr>
            <tr><td>Entre 20 dias e a data do evento</td><td>100% do total da carta</td></tr>
          </table>
          <p><i>Em caso de no show de apartamentos ou saída antecipada, será cobrado o total de diárias do período contratado.</i></p>

          <div class="assinatura">
            Atenciosamente,<br><br>
            <b>${nomeUsuario}</b><br>
            ${cargoUsuario}<br>
            📧 ${emailUsuario} | 📞 ${telUsuario}<br>
            <b>Ibis Budget São Paulo Paraíso</b>
          </div>
          
          <p style="margin-top: 30px; font-weight: bold; text-align: center;">Como deseja proceder com esta proposta?</p>
          
          <div class="botoes">
            <a href="${scriptUrl}?id=${idProposta}&nome=${encodeURIComponent(nomeCliente)}&acao=aceitar&lido=1" class="btn btn-aceitar">✅ Aceitar Proposta</a>
            <button onclick="mostrarCampoAjuste()" class="btn btn-ajuste">🔄 Solicitar Ajustes</button>
            <a href="${scriptUrl}?id=${idProposta}&nome=${encodeURIComponent(nomeCliente)}&acao=recusardireto&lido=1" class="btn btn-recusar">❌ Recusar</a>
          </div>

          <div id="bloco-ajuste" class="box-ajuste">
            <form onsubmit="enviarAjuste(event)">
              <label for="textoAjuste"><b>Descreva os ajustes necessários:</b></label><br>
              <textarea id="textoAjuste" placeholder="Ex: Precisamos alterar a data do check-out para o dia..."></textarea>
              <br>
              <button type="submit" class="btn btn-aceitar" style="margin-top: 10px; padding: 8px 15px;">Enviar Solicitação de Ajuste</button>
            </form>
          </div>
        </div>
      </body>
    </html>
  `);
}

function doPost(e) {
  return doGet(e);
}
