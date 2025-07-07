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

HelpDesk-web/
│
├── app.py # Arquivo principal do Flask
├── database/
│ └── db.py # Funções de conexão e queries SQL
├── templates/
│ ├── login.html
│ ├── cliente.html
│ ├── admin.html
│ └── visualizar_chamado.html
├── static/
│ ├── img/
│ │ └── fundo3.PNG # Imagem de fundo
│ └── uploads/ # Onde ficam os anexos
├── README.md
└── requirements.txt


---

## 📦 Como Executar Localmente

1. Clone o repositório:
   ```bash
   git clone https://github.com/weslleyjleles/helpdesk-flask.git
   cd helpdesk-flask

    Crie um ambiente virtual (recomendado):

python -m venv venv
venv\Scripts\activate  # Windows

Instale as dependências:

pip install -r requirements.txt

Configure o SQL Server com o banco HelpDeskDB e execute os scripts SQL iniciais (opcional).

Execute a aplicação:

    python app.py

    Acesse em: http://127.0.0.1:8050

📌 Observações

    Certifique-se de ter o SQL Server Express com o banco HelpDeskDB criado.

    A conexão está configurada no db.py para rodar localmente com Trusted Connection.

📸 Screenshots
<img src="static/img/painel-admin.png" width="700" alt="Painel do Administrador"> <img src="static/img/painel-cliente.png" width="700" alt="Painel do Cliente">
📄 Licença

Este projeto está licenciado sob a MIT License.
🤝 Autor

Desenvolvido por Weslley Leles
🔗 GitHub


---
