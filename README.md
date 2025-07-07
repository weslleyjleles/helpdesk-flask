# HelpDesk Web - Sistema de Suporte ao Cliente

Este é um sistema Help Desk desenvolvido com **Flask** (Python) e **SQL Server**, voltado para empresas que desejam gerenciar chamados de suporte de forma eficiente.  
Atualmente, o sistema já está preparado para uso real, com suporte a diferentes tipos de usuários e interface web responsiva via Bootstrap.

![Screenshot](static/img/screenshot.png)

---

## 🔧 Funcionalidades

### 👥 Acesso por níveis:
- **Cliente**: pode abrir chamados, enviar anexo, acompanhar respostas.
- **Administrador**: visualiza chamados do seu setor, responde e fecha chamados.
- **Superadministrador**: gerencia todos os chamados e usuários.

### 📌 Chamados:
- Cadastro de título, descrição, setor e imagem (anexo).
- Resposta por administrador com registro da data.
- Status: **Aberto**, **Respondido** e **Fechado**.
- Visualização detalhada dos chamados.

### 🧑‍💼 Gerenciamento de Usuários (superadmin):
- Cadastro de usuários (admin, cliente).
- Atribuição de setor ao administrador.
- Exclusão de usuários.

---

## 💻 Tecnologias Utilizadas

- Python 3.x
- Flask
- Jinja2
- Bootstrap 5
- SQL Server Express
- PyODBC

---

## 📁 Estrutura de Diretórios

