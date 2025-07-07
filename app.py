import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from database import db
from datetime import datetime
from unidecode import unidecode

# === Função para normalizar setor ===
def normalizar_setor(setor):
    return unidecode(setor.strip().lower()) if setor else None

app = Flask(__name__)
app.secret_key = "segredo"
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# === ROTA RAIZ / LOGIN ===
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        usuario_data = db.validar_login_retorna_dados(usuario, senha)
        if usuario_data:
            session['usuario'] = usuario_data['login']
            session['tipo'] = usuario_data['tipo']
            session['setor'] = normalizar_setor(usuario_data.get('setor'))

            if session['tipo'] == 'cliente':
                return redirect(url_for('painel_cliente'))
            elif session['tipo'] in ('admin', 'superadmin'):
                return redirect(url_for('painel_admin'))
            else:
                flash("Tipo de usuário não reconhecido.", "danger")
                return redirect(url_for('login'))
        else:
            flash('Login inválido', 'danger')
    return render_template('login.html')

# === LOGOUT ===
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# === PAINEL DO CLIENTE ===
@app.route('/cliente', methods=['GET', 'POST'])
def painel_cliente():
    if 'usuario' not in session or session['tipo'] != 'cliente':
        return redirect(url_for('login'))

    usuario = session['usuario']

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        setor = normalizar_setor(request.form.get('setor'))
        imagem = request.files.get('imagem')
        imagem_path = None

        if imagem and imagem.filename:
            filename = secure_filename(imagem.filename)
            caminho = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagem.save(caminho)
            imagem_path = filename

        db.salvar_chamado(titulo, setor, descricao, imagem_path, usuario)
        flash('Chamado enviado com sucesso!', 'success')
        return redirect(url_for('painel_cliente'))

    chamados = db.carregar_chamados_cliente(usuario)
    return render_template('cliente.html', usuario=usuario, chamados=chamados)

# === PAINEL DO ADMINISTRADOR E SUPERADMIN ===
@app.route('/admin', methods=['GET'])
def painel_admin():
    if 'usuario' not in session or session['tipo'] not in ('admin', 'superadmin'):
        return redirect(url_for('login'))

    tipo = session.get('tipo')
    setor = normalizar_setor(session.get('setor'))
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = 10
    offset = (pagina - 1) * por_pagina

    if tipo == 'superadmin':
        chamados = db.buscar_chamados_paginados(offset=offset, limite=por_pagina)
        total = db.contar_total_chamados()
    elif tipo == 'admin' and setor:
        chamados = db.buscar_chamados_por_setor(setor, offset, por_pagina)
        total = db.contar_total_chamados_setor(setor)
    else:
        chamados = []
        total = 0

    total_paginas = (total + por_pagina - 1) // por_pagina

    return render_template(
        'admin.html',
        usuario=session['usuario'],
        tipo=tipo,
        chamados=chamados,
        pagina=pagina,
        total_paginas=total_paginas
    )

# === RESPONDER CHAMADO ===
@app.route('/responder/<int:id>', methods=['POST'])
def responder_chamado_route(id):
    if 'usuario' not in session or session['tipo'] not in ('admin', 'superadmin'):
        return redirect(url_for('login'))

    resposta = request.form['resposta']
    db.responder_chamado(id, resposta)
    flash('Resposta enviada com sucesso!', 'success')
    return redirect(url_for('painel_admin'))

# === FECHAR CHAMADO ===
@app.route('/fechar/<int:id>', methods=['POST'])
def fechar_chamado_route(id):
    if 'usuario' not in session or session['tipo'] not in ('admin', 'superadmin'):
        return redirect(url_for('login'))

    db.fechar_chamado(id)
    flash('Chamado fechado com sucesso!', 'info')
    return redirect(url_for('painel_admin'))

# === SERVIR ANEXOS ===
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# === LISTAR USUÁRIOS (APENAS SUPERADMIN) ===
@app.route('/admin/usuarios', methods=['GET'])
def listar_usuarios():
    if 'usuario' not in session or session['tipo'] != 'superadmin':
        return redirect(url_for('login'))

    usuarios = db.consultar_usuarios_sql()
    return render_template('usuarios.html', usuarios=usuarios, usuario=session['usuario'])

# === CADASTRAR NOVO USUÁRIO (APENAS SUPERADMIN) ===
@app.route('/admin/usuarios/novo', methods=['GET', 'POST'])
def cadastrar_usuario():
    if 'usuario' not in session or session['tipo'] != 'superadmin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        login = request.form['login']
        senha = request.form['senha']
        tipo = request.form['tipo']
        setor = normalizar_setor(request.form.get('setor')) if tipo == 'admin' else None

        sucesso, msg = db.cadastrar_usuario_sql(login, senha, tipo, setor)
        flash(msg, 'success' if sucesso else 'danger')
        return redirect(url_for('listar_usuarios'))

    return render_template('cadastro_usuario.html', usuario=session['usuario'])

# === EXCLUIR USUÁRIO (APENAS SUPERADMIN) ===
@app.route('/admin/usuarios/excluir/<login>', methods=['POST'])
def excluir_usuario(login):
    if 'usuario' not in session or session['tipo'] != 'superadmin':
        return redirect(url_for('login'))

    if login == session['usuario']:
        flash("Você não pode excluir seu próprio usuário.", "warning")
    else:
        sucesso, msg = db.excluir_usuario_sql(login)
        flash(msg, "success" if sucesso else "danger")

    return redirect(url_for('listar_usuarios'))
@app.route('/admin/ver/<int:id>', endpoint='visualizar_chamado')
def visualizar_chamado(id):
    if 'usuario' not in session or session['tipo'] not in ('admin', 'superadmin'):
        return redirect(url_for('login'))

    chamado = db.buscar_chamado_por_id(id)
    if not chamado:
        flash("Chamado não encontrado", "danger")
        return redirect(url_for('painel_admin'))

    return render_template('visualizar_chamado.html', chamado=chamado)

# === INICIAR APP ===
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True, port=8050, host='127.0.0.1')
