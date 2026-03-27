import os
import uuid
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from unidecode import unidecode

# Importação das funções do banco de dados
from database.db import (
    validar_login_retorna_dados, salvar_chamado, carregar_chamados_cliente,
    buscar_chamado_por_id, buscar_chamados_paginados, contar_total_chamados,
    responder_chamado_com_anexo, fechar_chamado, consultar_usuarios_sql,
    cadastrar_usuario_sql, excluir_usuario_sql, contar_chamados_por_status, 
    chamados_por_mes, buscar_email_usuario, contar_chamados_por_setor
)
from util_email import enviar_email, montar_email_por_setor

app = Flask(__name__)
app.secret_key = "segredo_super_seguro" 
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Funções Auxiliares ---

def normalizar_setor(setor):
    return unidecode(setor.strip().lower()) if setor else None

def login_required(roles=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario' not in session:
                return redirect(url_for('login'))
            
            user_type = session['usuario'].get('tipo')
            if roles and user_type not in roles:
                flash('Acesso negado: área restrita.', 'danger')
                return redirect(url_for('painel_cliente' if user_type == 'cliente' else 'painel_admin'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def salvar_arquivo(arquivo, setor_raw):
    if not arquivo or not arquivo.filename:
        return None
    ext = os.path.splitext(arquivo.filename)[1]
    filename = secure_filename(f"{uuid.uuid4().hex}{ext}")
    setor = normalizar_setor(setor_raw) or 'geral'
    pasta_destino = os.path.join(app.config['UPLOAD_FOLDER'], setor)
    os.makedirs(pasta_destino, exist_ok=True)
    arquivo.save(os.path.join(pasta_destino, filename))
    return f"{setor}/{filename}"

# === ROTAS DE LOGIN E LOGOUT ===

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        usuario_data = validar_login_retorna_dados(usuario, senha)
        
        if usuario_data:
            session.permanent = True
            session['usuario'] = {
                'login': str(usuario_data['login']).strip(),
                'tipo': usuario_data['tipo'],
                'setor': usuario_data.get('setor')
            }
            destino = 'painel_cliente' if usuario_data['tipo'] == 'cliente' else 'painel_admin'
            return redirect(url_for(destino))
            
        flash('Login ou senha inválidos', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# === VISUALIZAÇÃO ===

@app.route('/chamado/visualizar/<int:id>')
@login_required(roles=['cliente', 'admin', 'superadmin'])
def visualizar_chamado(id):
    chamado = buscar_chamado_por_id(id)
    if not chamado:
        flash("Chamado não encontrado.", "danger")
        return redirect(url_for('painel_cliente' if session['usuario']['tipo'] == 'cliente' else 'painel_admin'))
    
    # Validação de segurança para clientes não verem chamados de outros
    if session['usuario']['tipo'] == 'cliente':
        login_sessao = session['usuario']['login'].lower()
        dono_chamado = chamado['usuario'].lower()
        if login_sessao != dono_chamado:
            flash("Você não tem permissão para visualizar este chamado.", "danger")
            return redirect(url_for('painel_cliente'))

    return render_template('visualizar_chamado.html', chamado=chamado)

# === PAINÉIS ===

@app.route('/cliente', methods=['GET', 'POST'])
@login_required(roles=['cliente'])
def painel_cliente():
    usuario = session['usuario']['login']
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        setor = request.form.get('setor')
        img_path = salvar_arquivo(request.files.get('imagem'), setor)
        salvar_chamado(titulo, setor, descricao, img_path, usuario)
        flash('Chamado aberto com sucesso!', 'success')
        return redirect(url_for('painel_cliente'))

    chamados = carregar_chamados_cliente(usuario)
    return render_template('cliente.html', usuario=usuario, chamados=chamados)

@app.route('/admin')
@login_required(roles=['admin', 'superadmin'])
def painel_admin():
    tipo = session['usuario']['tipo']
    setor_user = session['usuario'].get('setor') or 'geral'
    
    pagina = request.args.get('pagina', 1, type=int)
    status = request.args.get('status')
    setor_filtro = request.args.get('setor') if tipo == 'superadmin' else setor_user

    limite = 10
    offset = (pagina - 1) * limite
    chamados = buscar_chamados_paginados(offset, limite, status, setor_filtro)
    total = contar_total_chamados(status, setor_filtro)
    
    return render_template('admin.html', 
                           chamados=chamados, 
                           total_paginas=(total + limite - 1) // limite,
                           pagina=pagina,
                           tipo=tipo)

@app.route('/admin/dashboard')
@login_required(roles=['admin', 'superadmin'])
def dashboard():
    stats_status = contar_chamados_por_status() or {}
    stats_setor = contar_chamados_por_setor() or {}
    res_mes = chamados_por_mes()
    
    l_mes = res_mes[0] if (res_mes and len(res_mes) > 0) else []
    v_mes = res_mes[1] if (res_mes and len(res_mes) > 1) else []
    
    return render_template('dashboard.html', 
                           status_counts=stats_status, 
                           setor_counts=stats_setor, 
                           labels=l_mes,    
                           valores=v_mes)   

@app.route('/admin/usuarios')
@login_required(roles=['superadmin'])
def listar_usuarios():
    usuarios = consultar_usuarios_sql()
    return render_template('usuarios.html', usuarios=usuarios, usuario=session['usuario']['login'])

@app.route('/admin/cadastrar_usuario', methods=['POST'])
@login_required(roles=['superadmin'])
def cadastrar_usuario():
    login_form = request.form.get('login')
    senha_form = request.form.get('senha')
    tipo_form = request.form.get('tipo')
    setor_form = request.form.get('setor')
    email_form = request.form.get('email')

    sucesso, mensagem = cadastrar_usuario_sql(
        usuario=login_form, senha_plana=senha_form, 
        tipo=tipo_form, setor=setor_form, email=email_form
    )
    flash(mensagem, 'success' if sucesso else 'danger')
    return redirect(url_for('listar_usuarios'))

@app.route('/admin/excluir_usuario/<login_user>', methods=['POST'])
@login_required(roles=['superadmin'])
def excluir_usuario(login_user):
    sucesso, mensagem = excluir_usuario_sql(login_user)
    flash(mensagem, 'success' if sucesso else 'danger')
    return redirect(url_for('listar_usuarios'))

@app.route('/responder/<int:id>', methods=['POST'])
@login_required(roles=['admin', 'superadmin'])
def responder_chamado_route(id):
    resposta = request.form['resposta']
    anexo = salvar_arquivo(request.files.get('anexoResposta'), session['usuario'].get('setor'))
    
    # 1. Salva a resposta no banco
    responder_chamado_com_anexo(id, resposta, anexo)
    
    # 2. Tenta enviar e-mail de notificação
    try:
        chamado = buscar_chamado_por_id(id)
        email = buscar_email_usuario(chamado["usuario"])
        if email:
            # Importante: status_finalizado=False para e-mail de resposta
            assunto, msg = montar_email_por_setor(chamado, resposta, status_finalizado=False)
            enviar_email(email, assunto, msg)
    except Exception as e:
        print(f"Erro ao disparar e-mail de resposta: {e}")

    flash('Resposta enviada com sucesso!', 'success')
    return redirect(url_for('painel_admin'))

@app.route('/fechar/<int:id>', methods=['POST'])
@login_required(roles=['admin', 'superadmin'])
def fechar_chamado_route(id):
    print(f"\n>>> INICIANDO FECHAMENTO DO CHAMADO #{id}")
    
    chamado = buscar_chamado_por_id(id)
    if not chamado:
        return redirect(url_for('painel_admin'))

    try:
        fechar_chamado(id)
        usuario_chamado = chamado.get("usuario")
        email_cliente = buscar_email_usuario(usuario_chamado)

        if email_cliente:
            print(f">>> Email encontrado: {email_cliente}. Enviando aviso de fechamento...")
            assunto, msg_html = montar_email_por_setor(chamado, status_finalizado=True)
            enviar_email(email_cliente, assunto, msg_html)
        else:
            print(">>> AVISO: E-mail não enviado (campo vazio no banco).")

        flash(f'Chamado #{id} encerrado com sucesso!', 'success')
        
    except Exception as e:
        print(f">>> EXCEÇÃO NO FECHAMENTO: {e}")
        flash('Chamado encerrado, mas houve um erro na notificação por e-mail.', 'warning')

    return redirect(url_for('painel_admin'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(host='0.0.0.0', port=8050, debug=True)