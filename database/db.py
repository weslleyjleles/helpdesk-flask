import pyodbc
from datetime import datetime
from unidecode import unidecode

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
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT tipo FROM Usuarios WHERE login = ? AND senha = ?",
        (usuario.strip(), senha.strip())
    )
    resultado = cursor.fetchone()
    conn.close()
    return resultado[0] if resultado else None

def validar_login_retorna_dados(login, senha):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT login, tipo, setor FROM Usuarios WHERE login=? AND senha=?",
        (login.strip(), senha.strip())
    )
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
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Usuarios (login, senha, tipo, setor) VALUES (?, ?, ?, ?)",
            (usuario.strip(), senha.strip(), tipo, normalizar_setor(setor) if tipo == "admin" else None)
        )
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

# === CHAMADOS ===
def salvar_chamado(titulo, setor, descricao, imagem_path, usuario):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Chamados (titulo, descricao, imagem_path, data_abertura, status, usuario, setor)
        VALUES (?, ?, ?, ?, 'Aberto', ?, ?)
    """, (titulo, descricao, imagem_path, datetime.now(), usuario, normalizar_setor(setor)))
    conn.commit()
    conn.close()

def buscar_chamados_paginados(offset=0, limite=10, status=None, setor=None):
    conn = conectar()
    cursor = conn.cursor()
    query = """
        SELECT id, titulo, usuario, setor, data_abertura, status, imagem_path, resposta
        FROM chamados
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if setor:
        query += " AND LOWER(REPLACE(setor, ' ', '')) = ?"
        params.append(setor.replace(" ", "").lower())

    query += " ORDER BY id DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    params.extend([offset, limite])

    cursor.execute(query, params)
    resultados = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r[0], "titulo": r[1], "usuario": r[2],
            "setor": r[3], "data": r[4], "status": r[5],
            "anexo": r[6], "resposta": r[7]
        }
        for r in resultados
    ]

def buscar_chamados_por_setor(setor, offset=0, limite=10, status=None):
    return buscar_chamados_paginados(offset, limite, status, setor)

def contar_total_chamados(status=None, setor=None):
    conn = conectar()
    cursor = conn.cursor()
    query = "SELECT COUNT(*) FROM Chamados WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if setor:
        query += " AND LTRIM(RTRIM(LOWER(setor))) = ?"
        params.append(normalizar_setor(setor))

    cursor.execute(query, params)
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return total

def buscar_chamado_por_id(id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, titulo, descricao, usuario, setor, data_abertura, status,
               imagem_path, resposta, resposta_anexo
        FROM Chamados
        WHERE id = ?
    """, (id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    data_formatada = "-"
    try:
        if isinstance(row[5], datetime):
            data_formatada = row[5].strftime("%d/%m/%Y %H:%M")
        elif row[5]:
            data_convertida = datetime.fromisoformat(str(row[5]))
            data_formatada = data_convertida.strftime("%d/%m/%Y %H:%M")
    except:
        data_formatada = str(row[5])

    return {
        "id": row[0],
        "titulo": row[1] or "-",
        "descricao": row[2] or "Sem descrição.",
        "usuario": row[3] or "-",
        "setor": row[4] or "-",
        "data_abertura": data_formatada,
        "status": row[6] or "Desconhecido",
        "anexo": row[7],
        "resposta": row[8] or None,
        "resposta_anexo": row[9] or None
    }

def carregar_chamados_cliente(usuario):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, titulo, descricao, imagem_path, data_abertura,
               status, resposta, setor, usuario
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
            "setor": row[7] if len(row) > 7 else "",
            "usuario": row[8] if len(row) > 8 else ""
        })

    return chamados

def responder_chamado_com_anexo(id_chamado, resposta, anexo_path=None):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Chamados
        SET resposta = ?, status = 'Respondido', resposta_anexo = ?
        WHERE id = ?
    """, (resposta, anexo_path, id_chamado))
    conn.commit()
    conn.close()

def responder_chamado(id_chamado, resposta):
    responder_chamado_com_anexo(id_chamado, resposta, None)

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

# === NORMALIZAR SETORES ===
def normalizar_setores_usuarios():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT login, setor FROM Usuarios WHERE setor IS NOT NULL")
    usuarios = cursor.fetchall()

    for login, setor in usuarios:
        setor_normalizado = normalizar_setor(setor)
        cursor.execute("UPDATE Usuarios SET setor = ? WHERE login = ?", (setor_normalizado, login))

    conn.commit()
    conn.close()
    print("✅ Setores da tabela 'Usuarios' normalizados com sucesso.")

def normalizar_setores_chamados():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, setor FROM Chamados WHERE setor IS NOT NULL")
    chamados = cursor.fetchall()

    for chamado_id, setor in chamados:
        setor_normalizado = normalizar_setor(setor)
        cursor.execute("UPDATE Chamados SET setor = ? WHERE id = ?", (setor_normalizado, chamado_id))

    conn.commit()
    conn.close()
    print("✅ Setores da tabela 'Chamados' normalizados com sucesso.")

# === DASHBOARD ===

def contar_chamados_por_status():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT status, COUNT(*) 
        FROM Chamados
        GROUP BY status
    """)

    resultados = cursor.fetchall()
    conn.close()

    dados = {}
    for status, total in resultados:
        dados[status] = total

    return dados


def chamados_por_mes():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            MONTH(data_abertura) as mes,
            COUNT(*) as total
        FROM Chamados
        GROUP BY MONTH(data_abertura)
        ORDER BY mes
    """)

    resultados = cursor.fetchall()
    conn.close()

    labels = []
    valores = []

    for mes, total in resultados:
        labels.append(f"Mês {mes}")
        valores.append(total)

    return labels, valores

# === EXECUÇÃO LOCAL ===
if __name__ == "__main__":
    normalizar_setores_usuarios()
    normalizar_setores_chamados()
