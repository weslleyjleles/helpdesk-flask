import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from database import db
from datetime import datetime
from unidecode import unidecode
from database.db import contar_chamados_por_status, chamados_por_mes

def normalizar_setor(setor):
    return unidecode(setor.strip().lower()) if setor else None

app = Flask(__name__)
app.secret_key = "segredo"
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# === LOGIN ===
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        usuario_data = db.validar_login_retorna_dados(usuario, senha)
        if usuario_data:
            session['usuario'] = usuario_data
            return redirect(url_for('painel_cliente' if usuario_data['tipo'] == 'cliente' else 'painel_admin'))
        else:
            flash('Login inválido', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# === PAINEL CLIENTE ===
@app.route('/cliente', methods=['GET', 'POST'])
def painel_cliente():
    if 'usuario' not in session or session['usuario']['tipo'] != 'cliente':
        return redirect(url_for('login'))

    usuario = session['usuario']['login']

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        setor = normalizar_setor(request.form.get('setor'))
        imagem = request.files.get('imagem')
        imagem_path = None

        if imagem and imagem.filename:
            filename = secure_filename(imagem.filename)
            pasta_setor = os.path.join(app.config['UPLOAD_FOLDER'], setor or 'geral')
            os.makedirs(pasta_setor, exist_ok=True)
            caminho = os.path.join(pasta_setor, filename)
            imagem.save(caminho)
            imagem_path = f"{setor}/{filename}" if setor else filename

        db.salvar_chamado(titulo, setor, descricao, imagem_path, usuario)
        flash('Chamado enviado com sucesso!', 'success')
        return redirect(url_for('painel_cliente'))

    chamados = db.carregar_chamados_cliente(usuario)
    return render_template('cliente.html', usuario=usuario, chamados=chamados)

@app.route('/cliente/ver/<int:id>')
def visualizar_chamado_cliente(id):
    if 'usuario' not in session or session['usuario']['tipo'] != 'cliente':
        return redirect(url_for('login'))

    usuario = session['usuario']['login']
    chamado = db.buscar_chamado_por_id(id)

    if not chamado or chamado["usuario"] != usuario:
        flash('Chamado não encontrado ou acesso negado.', 'danger')
        return redirect(url_for('painel_cliente'))

    return render_template('detalhes_cliente.html', chamado=chamado)

# === PAINEL ADMIN ===
@app.route('/admin', methods=['GET'])
def painel_admin():
    if 'usuario' not in session or session['usuario']['tipo'] not in ('admin', 'superadmin'):
        return redirect(url_for('login'))

    tipo = session['usuario']['tipo']

    # Obtem o setor da sessão e normaliza, com fallback para 'geral'
    setor_raw = session['usuario'].get('setor')
    setor_normalizado = normalizar_setor(setor_raw) if setor_raw else 'geral'

    pagina = request.args.get('pagina', 1, type=int)
    status = request.args.get('status')

    # Se for superadmin, pode usar filtro de setor da URL; senão, usa o setor do admin atual
    setor_filtro = request.args.get('setor') if tipo == 'superadmin' else setor_normalizado

    por_pagina = 10
    offset = (pagina - 1) * por_pagina

    chamados = db.buscar_chamados_paginados(offset=offset, limite=por_pagina, status=status, setor=setor_filtro)
    total = db.contar_total_chamados(status=status, setor=setor_filtro)
    total_paginas = (total + por_pagina - 1) // por_pagina

    return render_template(
        'admin.html',
        usuario=session['usuario']['login'],
        tipo=tipo,
        chamados=chamados,
        pagina=pagina,
        total_paginas=total_paginas,
        status=status
    )


@app.route('/responder/<int:id>', methods=['POST'])
def responder_chamado_route(id):
    if 'usuario' not in session or session['usuario']['tipo'] not in ('admin', 'superadmin'):
        return redirect(url_for('login'))

    resposta = request.form['resposta']
    anexo_file = request.files.get('anexoResposta')
    anexo_path = None

    if anexo_file and anexo_file.filename:
        filename = secure_filename(anexo_file.filename)
        setor = normalizar_setor(session['usuario'].get('setor')) or 'geral'
        pasta_setor = os.path.join(app.config['UPLOAD_FOLDER'], setor)
        os.makedirs(pasta_setor, exist_ok=True)
        caminho = os.path.join(pasta_setor, filename)
        anexo_file.save(caminho)
        anexo_path = f"{setor}/{filename}"

    db.responder_chamado_com_anexo(id, resposta, anexo_path)
    flash('Resposta enviada com sucesso!', 'success')
    return redirect(url_for('painel_admin'))

@app.route('/fechar/<int:id>', methods=['POST'])
def fechar_chamado_route(id):
    if 'usuario' not in session or session['usuario']['tipo'] not in ('admin', 'superadmin'):
        return redirect(url_for('login'))

    db.fechar_chamado(id)
    flash('Chamado fechado com sucesso!', 'info')
    return redirect(url_for('painel_admin'))

@app.route('/admin/ver/<int:id>', endpoint='visualizar_chamado')
def visualizar_chamado(id):
    if 'usuario' not in session or session['usuario']['tipo'] not in ('admin', 'superadmin'):
        return redirect(url_for('login'))

    chamado = db.buscar_chamado_por_id(id)
    if not chamado:
        flash("Chamado não encontrado", "danger")
        return redirect(url_for('painel_admin'))

    return render_template('visualizar_chamado.html', chamado=chamado)

# === USUÁRIOS ===
@app.route('/admin/usuarios')
def listar_usuarios():
    if 'usuario' not in session or session['usuario']['tipo'] != 'superadmin':
        return redirect(url_for('login'))

    usuarios = db.consultar_usuarios_sql()
    return render_template('usuarios.html', usuarios=usuarios, usuario=session['usuario']['login'])

@app.route('/admin/cadastrar_usuario', methods=['POST'])
def cadastrar_usuario():
    if 'usuario' not in session or session['usuario']['tipo'] != 'superadmin':
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('login'))

    login = request.form['login']
    senha = request.form['senha']
    tipo = request.form['tipo']
    setor = request.form.get('setor', '')

    if db.validar_login(login, senha):
        flash('Usuário já existe', 'danger')
    else:
        db.cadastrar_usuario_sql(login, senha, tipo, setor)
        flash('Usuário cadastrado com sucesso', 'success')

    return redirect(url_for('listar_usuarios'))

@app.route('/excluir_usuario/<login>', methods=['POST'])
def excluir_usuario(login):
    if 'usuario' not in session or session['usuario']['tipo'] != 'superadmin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('listar_usuarios'))

    sucesso, msg = db.excluir_usuario_sql(login)
    categoria = 'success' if sucesso else 'danger'
    flash(msg, categoria)
    return redirect(url_for('listar_usuarios'))

# === DOWNLOAD DE ARQUIVO ===
@app.route('/uploads/<path:filename>')  # <path:filename> permite subpastas
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/dashboard")
def dashboard():
    status_counts = contar_chamados_por_status()
    labels, valores = chamados_por_mes()

    total = sum(status_counts.values())
    abertos = status_counts.get("Aberto", 0)
    respondidos = status_counts.get("Respondido", 0)
    fechados = status_counts.get("Fechado", 0)

    return render_template(
        "dashboard.html",
        total=total,
        abertos=abertos,
        respondidos=respondidos,
        fechados=fechados,
        labels=labels,
        valores=valores,
        status_counts=status_counts
    )


# === INICIALIZAÇÃO ===
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(host='0.0.0.0', port=8050, debug=True)