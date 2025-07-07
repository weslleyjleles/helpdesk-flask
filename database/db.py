import pyodbc
from datetime import datetime
from unidecode import unidecode
from datetime import datetime

# === Função para normalizar setores ===
def normalizar_setor(setor):
    return unidecode(setor.strip().lower()) if setor else None

# === CONEXÃO COM SQL SERVER ===
def conectar():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=HelpDeskDB;'
        'Trusted_Connection=yes;'
    )

# === USUÁRIOS ===
def validar_login(usuario, senha):
    usuario = usuario.strip()
    senha = senha.strip()
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT tipo FROM Usuarios WHERE login = ? AND senha = ?", (usuario, senha))
    resultado = cursor.fetchone()
    conn.close()
    return resultado[0] if resultado else None

def validar_login_retorna_dados(login, senha):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT login, tipo, setor FROM Usuarios WHERE login=? AND senha=?", (login.strip(), senha.strip()))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'login': row[0],
            'tipo': row[1],
            'setor': normalizar_setor(row[2])
        }
    return None

def cadastrar_usuario_sql(usuario, senha, tipo="cliente", setor=None):
    usuario = usuario.strip()
    senha = senha.strip()
    setor = normalizar_setor(setor) if tipo == "admin" else None

    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Usuarios (login, senha, tipo, setor) VALUES (?, ?, ?, ?)", (usuario, senha, tipo, setor))
        conn.commit()
        return True, "Usuário cadastrado com sucesso."
    except pyodbc.IntegrityError:
        return False, "Usuário já existe."
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def consultar_usuarios_sql():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT login, tipo FROM Usuarios ORDER BY login")
    resultados = cursor.fetchall()
    conn.close()
    return [{"login": row[0], "tipo": row[1]} for row in resultados]

def excluir_usuario_sql(login):
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Usuarios WHERE login = ?", (login,))
        conn.commit()
        return True, f"Usuário '{login}' excluído com sucesso."
    except Exception as e:
        return False, f"Erro ao excluir: {str(e)}"
    finally:
        conn.close()

# === ABRIR CHAMADO ===
def salvar_chamado(titulo, setor, descricao, imagem_path, usuario):
    setor = normalizar_setor(setor)
    conn = conectar()
    cursor = conn.cursor()
    data_abertura = datetime.now()
    cursor.execute("""
        INSERT INTO Chamados (titulo, descricao, imagem_path, data_abertura, status, usuario, setor)
        VALUES (?, ?, ?, ?, 'Aberto', ?, ?)
    """, (titulo, descricao, imagem_path, data_abertura, usuario, setor))
    conn.commit()
    conn.close()

# === LISTAR TODOS OS CHAMADOS ===
def buscar_chamados_paginados(offset=0, limite=10):
    conn = conectar()
    cursor = conn.cursor()
    query = """
    SELECT id, titulo, usuario, setor, data_abertura, status, imagem_path AS anexo, resposta
    FROM Chamados
    ORDER BY data_abertura DESC
    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    cursor.execute(query, (offset, limite))
    resultados = cursor.fetchall()
    colunas = [col[0] for col in cursor.description]

    chamados = []
    for row in resultados:
        dados = dict(zip(colunas, row))
        dados['data'] = dados['data_abertura'].strftime("%d/%m/%Y %H:%M") if dados['data_abertura'] else ""
        chamados.append(dados)

    cursor.close()
    conn.close()
    return chamados

def buscar_chamado_por_id(id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, descricao, usuario, setor, data_abertura, status, imagem_path, resposta FROM Chamados WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        # Verifica se a data está no formato datetime; senão, converte se possível
        data_formatada = "-"
        if row[5]:
            try:
                if isinstance(row[5], datetime):
                    data_formatada = row[5].strftime("%d/%m/%Y %H:%M")
                else:
                    # Tenta converter string para datetime se vier como texto
                    data_convertida = datetime.fromisoformat(str(row[5]))
                    data_formatada = data_convertida.strftime("%d/%m/%Y %H:%M")
            except Exception:
                data_formatada = str(row[5])  # Fallback

        return {
            "id": row[0],
            "titulo": row[1] or "-",
            "descricao": row[2] or "Sem descrição.",
            "usuario": row[3] or "-",
            "setor": row[4] or "-",
            "data_abertura": data_formatada,
            "status": row[6] or "Desconhecido",
            "anexo": row[7],
            "resposta": row[8] or None
        }
    return None





def buscar_chamados_por_tipo(tipo, setor=None, offset=0, limite=10):
    if tipo == "superadmin":
        return buscar_chamados_paginados(offset, limite)
    elif tipo == "admin" and setor:
        return buscar_chamados_por_setor(setor, offset, limite)
    else:
        return []

def contar_total_chamados_por_tipo(tipo, setor=None):
    if tipo == "superadmin":
        return contar_total_chamados()
    elif tipo == "admin" and setor:
        return contar_total_chamados_setor(setor)
    else:
        return 0

def contar_total_chamados():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Chamados")
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return total

# === CHAMADOS DE CLIENTE ===
def carregar_chamados_cliente(usuario):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, titulo, descricao, imagem_path, data_abertura, status, resposta, setor
        FROM Chamados
        WHERE usuario = ?
        ORDER BY data_abertura DESC
    """, (usuario,))
    resultados = cursor.fetchall()
    conn.close()

    chamados = []
    for row in resultados:
        chamados.append({
            "id": row[0],
            "titulo": row[1],
            "descricao": row[2],
            "anexo": row[3],
            "data": row[4].strftime("%d/%m/%Y %H:%M") if row[4] else "",
            "status": row[5],
            "resposta": row[6] if len(row) > 6 else "",
            "setor": row[7] if len(row) > 7 else ""
        })
    return chamados

# === RESPONDER CHAMADO ===
def responder_chamado(id_chamado, resposta):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Chamados
        SET resposta = ?, status = 'Respondido'
        WHERE id = ?
    """, (resposta, id_chamado))
    conn.commit()
    conn.close()

# === FECHAR CHAMADO ===
def fechar_chamado(id_chamado):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Chamados
        SET status = 'Fechado'
        WHERE id = ?
    """, (id_chamado,))
    conn.commit()
    conn.close()

# === CHAMADOS POR SETOR (usando normalização) ===
def buscar_chamados_por_setor(setor, offset=0, limite=10):
    setor = normalizar_setor(setor)
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, titulo, usuario, setor, data_abertura, status, imagem_path AS anexo, resposta
        FROM Chamados
        WHERE LTRIM(RTRIM(LOWER(setor))) = ?
        ORDER BY data_abertura DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """, (setor, offset, limite))
    resultados = cursor.fetchall()
    colunas = [col[0] for col in cursor.description]

    chamados = []
    for row in resultados:
        dados = dict(zip(colunas, row))
        dados['data'] = dados['data_abertura'].strftime("%d/%m/%Y %H:%M") if dados['data_abertura'] else ""
        chamados.append(dados)

    cursor.close()
    conn.close()
    return chamados

def contar_total_chamados_setor(setor):
    setor = normalizar_setor(setor)
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM Chamados
        WHERE LTRIM(RTRIM(LOWER(setor))) = ?
    """, (setor,))
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return total
