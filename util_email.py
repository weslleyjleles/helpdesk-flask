import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def enviar_email(destinatario, assunto, mensagem_html):
    remetente = "helpdesk@ciadoterno.com.br"
    senha = "123@qaz.wsx.edc." # Mantenha sua senha aqui

    msg = MIMEMultipart()
    msg["From"] = remetente
    msg["To"] = destinatario
    msg["Subject"] = assunto
    
    msg.attach(MIMEText(mensagem_html, "html"))

    try:
        # Aumentei o timeout para 15s para evitar quedas em redes instáveis
        with smtplib.SMTP("mail.ciadoterno.com.br", 587, timeout=15) as servidor:
            servidor.starttls() 
            servidor.login(remetente, senha)
            servidor.send_message(msg)
        print(f"Email enviado com sucesso para {destinatario}!")
        return True
    except smtplib.SMTPAuthenticationError:
        print("Erro de Autenticação: Verifique login/senha do SMTP.")
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
    return False

def montar_email_por_setor(chamado, resposta=None, status_finalizado=False):
    """
    Gera assunto e corpo do email adaptando-se para 'Resposta' ou 'Fechamento'.
    """
    setor_slug = str(chamado.get("setor", "")).strip().lower()

    assinaturas = {
        "ti": "Equipe de TI",
        "rh": "Recursos Humanos",
        "financeiro": "Financeiro",
        "beneficio": "Benefícios",
        "expedicao": "Expedição",
        "logistica": "Equipe de Logística",
        "dp": "Departamento Pessoal",
        "contabilidade": "Contabilidade",
    }

    nome_setor = assinaturas.get(setor_slug, "Suporte Geral")
    id_chamado = chamado.get('id', '000')
    titulo = chamado.get('titulo', 'Sem Título')

    # Define o Assunto e o Status baseado na ação
    if status_finalizado:
        assunto = f"✅ CHAMADO ENCERRADO #{id_chamado} - {nome_setor}"
        status_texto = "foi **ENCERRADO**"
        cor_status = "#28a745" # Verde
    else:
        assunto = f"✉️ Resposta no Chamado #{id_chamado} - {nome_setor}"
        status_texto = "recebeu uma nova **RESPOSTA**"
        cor_status = "#007bff" # Azul

    # Montagem do HTML com um visual um pouco mais profissional
    mensagem = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; border-radius: 8px;">
                <h2 style="color: {cor_status}; border-bottom: 2px solid {cor_status}; padding-bottom: 10px;">
                    CIA. DO TERNO - HelpDesk
                </h2>
                <p>Olá, <strong>{chamado.get('usuario', 'Usuário')}</strong>,</p>
                <p>O seu chamado <strong>"{titulo}"</strong> {status_texto} pelo setor <strong>{nome_setor}</strong>.</p>
                
                {f'<div style="background: #f9f9f9; padding: 15px; border-left: 4px solid {cor_status}; margin: 20px 0;"><strong>Resposta:</strong><br>{resposta}</div>' if resposta else ''}
                
                <p style="font-size: 0.9em; color: #666;">
                    Para acompanhar os detalhes, acesse o painel do sistema.
                </p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p>Atenciosamente,<br>
                <strong>{nome_setor}</strong><br>
                CIA. DO TERNO</p>
            </div>
        </body>
    </html>
    """

    return assunto, mensagem