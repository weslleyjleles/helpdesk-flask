import pyodbc
from unidecode import unidecode
from werkzeug.security import generate_password_hash, check_password_hash

# === CONFIGURAÇÃO DE CONEXÃO ===
def conectar():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=HelpDeskDB;'
        'Trusted_Connection=yes;'
    )

def normalizar_setor(setor):
    return unidecode(setor.strip().lower()) if setor else None

# === USUÁRIOS E SEGURANÇA ===

def validar_login_retorna_dados(login, senha_digitada):
    conn = conectar()
    cursor = conn.cursor()
    # Usamos RTRIM para evitar problemas com espaços em branco do SQL Server
    cursor.execute(
        "SELECT RTRIM(login), RTRIM(tipo), RTRIM(setor), senha FROM Usuarios WHERE RTRIM(login)=?",
        (login.strip(),)
    )
    row = cursor.fetchone()
    conn.close()

    if row and check_password_hash(row[3], senha_digitada.strip()):
        return {
            'login': row[0],
            'tipo': row[1],
            'setor': normalizar_setor(row[2])
        }
    return None

def cadastrar_usuario_sql(usuario, senha_plana, tipo="cliente", setor=None, email=None):
    conn = conectar()
    cursor = conn.cursor()
    senha_com_hash = generate_password_hash(senha_plana.strip())
    try:
        cursor.execute(
            "INSERT INTO Usuarios (login, senha, tipo, setor, email) VALUES (?, ?, ?, ?, ?)",
            (usuario.strip(), senha_com_hash, tipo, 
             normalizar_setor(setor) if tipo in ("admin", "superadmin") else None,
             email.strip() if email else None)
        )
        conn.commit()
        return True, "Usuário cadastrado com sucesso."
    except pyodbc.IntegrityError:
        return False, "Usuário já existe."
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def buscar_email_usuario(login):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT RTRIM(email) FROM Usuarios WHERE RTRIM(login) = ?", (login.strip(),))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def consultar_usuarios_sql():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT RTRIM(login), RTRIM(tipo), RTRIM(email) FROM Usuarios ORDER BY login")
    resultados = cursor.fetchall()
    conn.close()
    return [{"login": r[0], "tipo": r[1], "email": r[2]} for r in resultados]

def excluir_usuario_sql(login):
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Usuarios WHERE RTRIM(login) = ?", (login.strip(),))
        conn.commit()
        return True, f"Usuário '{login}' excluído."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

# === GESTÃO DE CHAMADOS ===

def salvar_chamado(titulo, setor, descricao, img_path, usuario):
    """Salva o chamado e retorna o ID gerado para vincular anexos."""
    conn = conectar()
    cursor = conn.cursor()
    query = """
        SET NOCOUNT ON;
        INSERT INTO Chamados (titulo, setor, descricao, imagem_path, usuario, data_abertura, status)
        VALUES (?, ?, ?, ?, ?, GETDATE(), 'Aberto');
        SELECT SCOPE_IDENTITY() AS id;
    """
    cursor.execute(query, (titulo, setor, descricao, img_path, usuario))
    row = cursor.fetchone()
    novo_id = row[0] if row else None
    conn.commit()
    conn.close()
    return int(novo_id) if novo_id else None

def salvar_anexo_no_banco(id_chamado, nome_arquivo, caminho_arquivo):
    """Consolidado: Salva o registro do anexo vinculado ao chamado."""
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Anexos (id_chamado, nome_arquivo, caminho_arquivo, data_upload)
            VALUES (?, ?, ?, GETDATE())
        """, (id_chamado, nome_arquivo, caminho_arquivo))
        conn.commit()
    except Exception as e:
        print(f"Erro ao salvar anexo no banco: {e}")
    finally:
        conn.close()
import os

def excluir_anexo_por_id(id_anexo):
    conn = conectar()
    cursor = conn.cursor()
    
    # 1. Buscar o caminho do arquivo para apagar do HD
    cursor.execute("SELECT caminho_arquivo FROM Anexos WHERE id_anexo = ?", (id_anexo,))
    row = cursor.fetchone()
    
    if row:
        caminho_arquivo = row[0]
        # Caminho completo no Windows/Linux
        # Ajuste o 'static' se sua pasta base for diferente
        caminho_completo = os.path.join(os.getcwd(), caminho_arquivo)
        
        try:
            # 2. Deleta o arquivo físico
            if os.path.exists(caminho_completo):
                os.remove(caminho_completo)
            
            # 3. Deleta o registro no Banco de Dados
            cursor.execute("DELETE FROM Anexos WHERE id_anexo = ?", (id_anexo,))
            conn.commit()
            return True, "Anexo excluído com sucesso."
        except Exception as e:
            return False, f"Erro ao excluir: {e}"
    
    conn.close()
    return False, "Anexo não encontrado."
def contar_total_chamados(status=None, setor=None):
    conn = conectar()
    cursor = conn.cursor()
    query = "SELECT COUNT(*) FROM Chamados WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if setor:
        query += " AND setor = ?"
        params.append(normalizar_setor(setor))
    cursor.execute(query, params)
    total = cursor.fetchone()[0]
    conn.close()
    return total

def buscar_chamados_paginados(offset=0, limite=10, status=None, setor=None):
    conn = conectar()
    cursor = conn.cursor()
    query = "SELECT id, titulo, RTRIM(usuario), setor, data_abertura, status, imagem_path, resposta FROM Chamados WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if setor:
        query += " AND setor = ?"
        params.append(normalizar_setor(setor))
    query += " ORDER BY id DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    params.extend([offset, limite])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [{
        "id": r[0], "titulo": r[1], "usuario": r[2], "setor": r[3],
        "data": r[4], "status": r[5], "anexo": r[6], "resposta": r[7]
    } for r in rows]

def carregar_chamados_cliente(usuario):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, titulo, status, data_abertura 
        FROM Chamados WHERE RTRIM(usuario) = ? 
        ORDER BY data_abertura DESC
    """, (usuario.strip(),))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "titulo": r[1], "status": r[2], "data": r[3]} for r in rows]

def buscar_chamado_por_id(id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, titulo, descricao, RTRIM(usuario), setor, 
               data_abertura, status, imagem_path, resposta 
        FROM Chamados WHERE id = ?
    """, (id,))
    r = cursor.fetchone()
    conn.close()
    if not r: return None
    return {
        "id": r[0], "titulo": r[1], "descricao": r[2], "usuario": r[3],
        "setor": r[4], "data_abertura": r[5], "status": r[6], "anexo": r[7], "resposta": r[8]
    }

def buscar_anexos_do_chamado(id_chamado):
    conn = conectar()
    cursor = conn.cursor()
    
    # ADICIONADO 'id_anexo' no SELECT
    cursor.execute("SELECT id_anexo, nome_arquivo, caminho_arquivo FROM Anexos WHERE id_chamado = ?", (id_chamado,))
    rows = cursor.fetchall()
    
    anexos = []
    for row in rows:
        anexos.append({
            'id_anexo': row[0],      # <--- AGORA O JINJA VAI ENCONTRAR ESSE ATRIBUTO
            'nome': row[1],
            'caminho': row[2]
        })
    
    conn.close()
    return anexos

def responder_chamado_com_anexo(id_chamado, resposta, anexo_path=None):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Chamados SET resposta = ?, status = 'Respondido', imagem_path = COALESCE(?, imagem_path) 
        WHERE id = ?
    """, (resposta, anexo_path, id_chamado))
    conn.commit()
    conn.close()

def fechar_chamado(id_chamado):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("UPDATE Chamados SET status = 'Fechado' WHERE id = ?", (id_chamado,))
    conn.commit()
    conn.close()

# === FUNÇÕES DE DASHBOARD ===

def contar_chamados_por_status():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) FROM Chamados GROUP BY status")
    res = cursor.fetchall()
    conn.close()
    return {r[0]: r[1] for r in res}

def contar_chamados_por_setor():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT RTRIM(setor), COUNT(*) FROM Chamados GROUP BY setor")
    res = cursor.fetchall()
    conn.close()
    return { (r[0] if r[0] else "Não Definido"): r[1] for r in res }

def chamados_por_mes():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT FORMAT(data_abertura, 'MM/yyyy') as mes, COUNT(*) 
        FROM Chamados GROUP BY FORMAT(data_abertura, 'MM/yyyy')
        ORDER BY mes
    """)
    res = cursor.fetchall()
    conn.close()
    return [r[0] for r in res], [r[1] for r in res]