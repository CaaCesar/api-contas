import json
import os
import calendar
from datetime import datetime
import ttkbootstrap as ttk
from tkinter import messagebox
import requests

# =====================================================================
# CAMADA DE DADOS (Conectada ao FastAPI)
# =====================================================================
class ControladorDeDados:
    def __init__(self):
        # Endereço onde o seu servidor FastAPI está rodando
        self.api_url = 'http://127.0.0.1:8000'
        
        # Não precisamos mais inicializar arquivos aqui, o backend cuida disso!

    def validar_login(self, usuario, senha):
        try:
            # POST /login
            resposta = requests.post(f"{self.api_url}/login", json={"usuario": usuario, "senha": senha})
            return resposta.status_code == 200
        except requests.exceptions.RequestException:
            raise Exception("Não foi possível conectar ao servidor. O FastAPI está rodando?")

    def criar_usuario(self, novo_user, nova_senha):
        try:
            # POST /usuarios
            resposta = requests.post(f"{self.api_url}/usuarios", json={"usuario": novo_user, "senha": nova_senha})
            if resposta.status_code == 200:
                return True, resposta.json().get("mensagem")
            else:
                return False, resposta.json().get("detail", "Erro desconhecido")
        except requests.exceptions.RequestException:
            return False, "Sem conexão com o servidor."

    def obter_meses_existentes(self):
        try:
            # GET /meses
            resposta = requests.get(f"{self.api_url}/meses")
            if resposta.status_code == 200:
                return resposta.json().get("meses", [])
            return []
        except requests.exceptions.RequestException:
            return []

    def criar_mes(self, chave_mes):
        try:
            # POST /meses
            resposta = requests.post(f"{self.api_url}/meses", json={"chave_mes": chave_mes})
            if resposta.status_code != 200:
                raise Exception(resposta.json().get("detail", "Erro ao criar mês"))
        except requests.exceptions.RequestException:
            raise Exception("Sem conexão com o servidor.")

    def obter_contas(self, mes_ano, tipo_conta):
        try:
            # GET /contas/{mes_ano}/{tipo_conta}
            resposta = requests.get(f"{self.api_url}/contas/{mes_ano}/{tipo_conta}")
            if resposta.status_code == 200:
                return resposta.json().get("contas", [])
            return []
        except requests.exceptions.RequestException:
            return []

    def adicionar_conta(self, mes_ano, tipo_conta, nova_conta):
        try:
            # POST /contas/{mes_ano}/{tipo_conta}
            resposta = requests.post(f"{self.api_url}/contas/{mes_ano}/{tipo_conta}", json=nova_conta)
            if resposta.status_code != 200:
                raise Exception("Erro ao adicionar conta no servidor")
        except requests.exceptions.RequestException:
            raise Exception("Sem conexão com o servidor.")

    def editar_conta(self, mes_ano, tipo_conta, descricao_antiga, data_antiga, conta_atualizada):
        try:
            # PUT /contas/{mes_ano}/{tipo_conta}
            payload = {
                "descricao_antiga": descricao_antiga,
                "data_antiga": data_antiga,
                "conta_atualizada": conta_atualizada
            }
            resposta = requests.put(f"{self.api_url}/contas/{mes_ano}/{tipo_conta}", json=payload)
            if resposta.status_code != 200:
                raise Exception("Erro ao editar conta no servidor")
        except requests.exceptions.RequestException:
            raise Exception("Sem conexão com o servidor.")

    def remover_conta(self, mes_ano, tipo_conta, descricao_alvo, data_alvo):
        try:
            # DELETE /contas/{mes_ano}/{tipo_conta}
            parametros = {"descricao": descricao_alvo, "data": data_alvo}
            resposta = requests.delete(f"{self.api_url}/contas/{mes_ano}/{tipo_conta}", params=parametros)
            if resposta.status_code != 200:
                raise Exception("Erro ao remover conta no servidor")
        except requests.exceptions.RequestException:
            raise Exception("Sem conexão com o servidor.")

    def obter_todos_logs(self):
        try:
            # GET /logs
            resposta = requests.get(f"{self.api_url}/logs")
            if resposta.status_code == 200:
                logs_api = resposta.json().get("logs", [])
                # Converte o dicionário que vem da API de volta para a tupla que o Tkinter espera
                return [(log["mes_ano"], log["tipo_conta"], log["conta"]) for log in logs_api]
            return []
        except requests.exceptions.RequestException:
            return []
# =====================================================================
# CAMADA DE INTERFACE VISUAL (Nosso Frontend em Tkinter)
# Responsável apenas por desenhar botões, tabelas e avisos na tela
# =====================================================================
class GerenciadorContas:
    def __init__(self, root):
        self.root = root
        self.root.title("Contas em Dia")
        self.root.geometry("800x650")
        
        # Conecta a interface gráfica com o "banco de dados"
        self.db = ControladorDeDados()
        
        self.mes_selecionado = None
        self.usuario_logado = None
        
        self.frame_atual = ttk.Frame(self.root, padding=20)
        self.frame_atual.pack(expand=True, fill='both')
        self.construir_tela_login()

    def limpar_tela(self):
        for widget in self.frame_atual.winfo_children():
            widget.destroy()

    # --- 1. LOGIN ---
    def construir_tela_login(self):
        self.limpar_tela()
        
        frame_centro = ttk.Frame(self.frame_atual)
        frame_centro.pack(expand=True)

        ttk.Label(frame_centro, text="Login", font=("Helvetica", 24, "bold")).pack(pady=20)
        
        ttk.Label(frame_centro, text="Usuário:", font=("Helvetica", 10)).pack(fill='x')
        self.entry_usuario = ttk.Entry(frame_centro)
        self.entry_usuario.pack(pady=5, fill='x')
        
        ttk.Label(frame_centro, text="Senha:", font=("Helvetica", 10)).pack(fill='x')
        self.entry_senha = ttk.Entry(frame_centro, show="*")
        self.entry_senha.pack(pady=5, fill='x')
        
        ttk.Button(frame_centro, text="Entrar", command=self.fazer_login, bootstyle="success").pack(pady=20, fill='x')

    def fazer_login(self):
        usuario = self.entry_usuario.get().strip()
        senha = self.entry_senha.get().strip()
        
        try:
            # Chama a camada de dados!
            if self.db.validar_login(usuario, senha):
                self.usuario_logado = usuario 
                self.construir_tela_meses()
            else:
                messagebox.showerror("Erro", "Usuário ou senha incorretos.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro no sistema: {e}")

    # --- 2. TELA DE MESES ---
    def construir_tela_meses(self, mensagem_status="", tipo_status="success"):
        self.limpar_tela()
        
        ttk.Label(self.frame_atual, text="Selecione o Mês / Ano", font=("Helvetica", 22, "bold")).pack(pady=(10, 10))
        
        if self.usuario_logado == "admin":
            ttk.Button(self.frame_atual, text="⚙️ Painel Administrador", bootstyle="warning", 
                       command=self.abrir_painel_admin).pack(pady=(0, 20))
        
        # Pede os meses existentes para a camada de dados
        meses_criados = self.db.obter_meses_existentes()

        ano_atual = datetime.now().year
        meses_num = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
        meses_nomes = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                       "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

        frame_grid = ttk.Frame(self.frame_atual)
        frame_grid.pack(expand=True)

        for i, mes in enumerate(meses_num):
            chave_mes = f"{mes}-{ano_atual}"
            linha = i // 3
            coluna = i % 3
            
            if chave_mes in meses_criados:
                texto_btn = f"{meses_nomes[i]}\n{ano_atual}"
                btn = ttk.Button(frame_grid, text=texto_btn, bootstyle="success",
                                 command=lambda c=chave_mes: self.abrir_planilha_mes(c))
            else:
                texto_btn = f"+ Criar\n{meses_nomes[i]} {ano_atual}"
                btn = ttk.Button(frame_grid, text=texto_btn, bootstyle="light",
                                 command=lambda c=chave_mes: self.criar_novo_mes(c))
                
            btn.grid(row=linha, column=coluna, padx=12, pady=12, ipadx=25, ipady=15, sticky='nsew')

        frame_rodape = ttk.Frame(self.frame_atual)
        frame_rodape.pack(side='bottom', fill='x', pady=10)
        self.lbl_status = ttk.Label(frame_rodape, text=mensagem_status, font=("Helvetica", 11), bootstyle=tipo_status)
        self.lbl_status.pack()

        if mensagem_status:
            self.root.after(4000, lambda: self.lbl_status.config(text="") if self.lbl_status.winfo_exists() else None)

    def criar_novo_mes(self, chave_mes):
        try:
            self.db.criar_mes(chave_mes)
            self.construir_tela_meses(f"Planilha de {chave_mes} criada com sucesso!", "success")
        except Exception as e:
            self.construir_tela_meses(f"Erro ao criar planilha: {e}", "danger")

    def abrir_planilha_mes(self, chave_mes):
        self.mes_selecionado = chave_mes
        self.construir_tela_principal()

    # --- 3. TELA PRINCIPAL DE CONTAS ---
    def construir_tela_principal(self):
        self.limpar_tela()
        
        frame_topo = ttk.Frame(self.frame_atual)
        frame_topo.pack(fill='x', pady=10)
        
        ttk.Button(frame_topo, text="⬅ Voltar aos Meses", bootstyle="secondary", command=self.construir_tela_meses).pack(side='left')
        ttk.Label(frame_topo, text=f"Gerenciando Contas: {self.mes_selecionado}", font=("Helvetica", 16, "bold")).pack(side='left', padx=20)

        self.notebook = ttk.Notebook(self.frame_atual, bootstyle="info")
        self.notebook.pack(fill='both', expand=True, pady=10)
        
        self.aba_fixas = ttk.Frame(self.notebook)
        self.aba_temporarias = ttk.Frame(self.notebook)
        self.aba_divisao = ttk.Frame(self.notebook)
        
        self.notebook.add(self.aba_fixas, text="Contas Fixas")
        self.notebook.add(self.aba_temporarias, text="Contas Temporárias")
        self.notebook.add(self.aba_divisao, text="Compras em Divisão")
        
        self.construir_interface_aba(self.aba_fixas, "fixas")
        self.construir_interface_aba(self.aba_temporarias, "temporarias")
        self.construir_interface_aba(self.aba_divisao, "divisao")

    def construir_interface_aba(self, parent, tipo_conta):
        frame_botoes = ttk.Frame(parent)
        frame_botoes.pack(fill='x', pady=5)
        
        frame_borda = ttk.Frame(parent, bootstyle="dark", padding=1)
        frame_borda.pack(fill='both', expand=True, pady=10)
        
        tabela = ttk.Treeview(frame_borda, columns=("Nome", "Valor", "Usuario", "Data"), show="headings")
        tabela.pack(fill='both', expand=True)

        tabela.column("Nome", anchor="w", width=250)
        tabela.column("Valor", anchor="center", width=120)
        tabela.column("Usuario", anchor="center", width=120)
        tabela.column("Data", anchor="center", width=150)
        
        tabela.heading("Nome", text="Descrição da Conta", anchor="w")
        tabela.heading("Valor", text="Valor (R$)", anchor="center")
        tabela.heading("Usuario", text="Criado Por", anchor="center")
        tabela.heading("Data", text="Data/Hora", anchor="center")
        
        frame_resultados = ttk.Frame(parent)
        frame_resultados.pack(fill='x', pady=10)
        
        lbl_total = ttk.Label(frame_resultados, text="Total: R$ 0.00", font=("Helvetica", 14, "bold"))
        lbl_total.pack(side='left', padx=20)
        
        lbl_divisao = ttk.Label(frame_resultados, text="Por pessoa (Divisão por 3): R$ 0.00", font=("Helvetica", 14))
        lbl_divisao.pack(side='left')

        ttk.Button(frame_botoes, text="+ Adicionar", bootstyle="primary", 
                   command=lambda tc=tipo_conta, tab=tabela, lt=lbl_total, ld=lbl_divisao: self.abrir_janela_adicao(tc, tab, lt, ld)).pack(side='left', padx=5)
        
        ttk.Button(frame_botoes, text="Editar", bootstyle="secondary",
                   command=lambda tc=tipo_conta, tab=tabela, lt=lbl_total, ld=lbl_divisao: self.abrir_janela_edicao(tc, tab, lt, ld)).pack(side='left', padx=5)
                   
        ttk.Button(frame_botoes, text="- Remover", bootstyle="danger",
                   command=lambda tc=tipo_conta, tab=tabela, lt=lbl_total, ld=lbl_divisao: self.remover_conta(tc, tab, lt, ld)).pack(side='left', padx=5)
        
        self.carregar_dados_tabela(tipo_conta, tabela, lbl_total, lbl_divisao)

    # --- 4. CRUD DE TABELAS ---
    def carregar_dados_tabela(self, tipo_conta, tabela, lbl_total, lbl_divisao):
        for item in tabela.get_children():
            tabela.delete(item)
            
        # Limpo e direto: Pede as contas para a camada de dados
        contas = self.db.obter_contas(self.mes_selecionado, tipo_conta)
        
        soma_total = 0.0
        for conta in contas:
            tabela.insert("", "end", values=(conta['descricao'], f"R$ {conta['valor']:.2f}", conta['usuario'], conta['data']))
            soma_total += float(conta['valor'])
            
        lbl_total.config(text=f"Total: R$ {soma_total:.2f}")
        lbl_divisao.config(text=f"Por pessoa (Divisão por 3): R$ {(soma_total / 3):.2f}")

    def abrir_janela_adicao(self, tipo_conta, tabela, lbl_total, lbl_divisao):
        janela = ttk.Toplevel(self.root)
        janela.title("Adicionar Conta")
        janela.geometry("300x250")
        janela.grab_set() 
        
        ttk.Label(janela, text="Descrição:").pack(pady=(10, 0), padx=20, fill='x')
        entry_desc = ttk.Entry(janela)
        entry_desc.pack(pady=5, padx=20, fill='x')
        
        ttk.Label(janela, text="Valor (R$):").pack(pady=(10, 0), padx=20, fill='x')
        entry_valor = ttk.Entry(janela)
        entry_valor.pack(pady=5, padx=20, fill='x')
        
        ttk.Button(janela, text="Salvar", bootstyle="success", 
                   command=lambda: self.salvar_nova_conta(janela, tipo_conta, tabela, entry_desc.get(), entry_valor.get(), lbl_total, lbl_divisao)
                  ).pack(pady=20)

    def salvar_nova_conta(self, janela, tipo_conta, tabela, descricao, valor_str, lbl_total, lbl_divisao):
        if not descricao or not valor_str:
            messagebox.showwarning("Aviso", "Preencha todos os campos!")
            return
            
        try:
            valor = float(valor_str.replace(',', '.')) 
        except ValueError:
            messagebox.showerror("Erro", "Digite um valor numérico válido.")
            return

        nova_conta = {
            "descricao": descricao,
            "valor": valor,
            "usuario": self.usuario_logado,
            "data": datetime.now().strftime("%d/%m/%Y %H:%M")
        }

        # Envia para a camada de dados salvar
        self.db.adicionar_conta(self.mes_selecionado, tipo_conta, nova_conta)
            
        janela.destroy()
        self.carregar_dados_tabela(tipo_conta, tabela, lbl_total, lbl_divisao)

    def remover_conta(self, tipo_conta, tabela, lbl_total, lbl_divisao):
        selecionado = tabela.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione uma conta na tabela para remover!")
            return

        valores = tabela.item(selecionado[0], 'values')
        descricao_alvo = valores[0]
        criador_da_conta = valores[2]
        data_alvo = valores[3]

        if self.usuario_logado != "admin" and self.usuario_logado != criador_da_conta:
            messagebox.showerror("Acesso Negado", "Você só tem permissão para apagar contas que você mesmo criou!")
            return

        resposta = messagebox.askyesno("Confirmar", f"Tem certeza que deseja remover a conta '{descricao_alvo}'?")
        if not resposta:
            return

        # Envia o comando de remoção para a camada de dados
        self.db.remover_conta(self.mes_selecionado, tipo_conta, descricao_alvo, data_alvo)

        self.carregar_dados_tabela(tipo_conta, tabela, lbl_total, lbl_divisao)

    def abrir_janela_edicao(self, tipo_conta, tabela, lbl_total, lbl_divisao):
        selecionado = tabela.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione uma conta na tabela para editar!")
            return

        valores = tabela.item(selecionado[0], 'values')
        descricao_atual = valores[0]
        valor_atual_str = valores[1].replace('R$ ', '') 
        criador_da_conta = valores[2]
        data_atual = valores[3]

        if self.usuario_logado != "admin" and self.usuario_logado != criador_da_conta:
            messagebox.showerror("Acesso Negado", "Você só tem permissão para editar contas que você mesmo criou!")
            return

        janela = ttk.Toplevel(self.root)
        janela.title("Editar Conta")
        janela.geometry("300x250")
        janela.grab_set()

        ttk.Label(janela, text="Descrição:").pack(pady=(10, 0), padx=20, fill='x')
        entry_desc = ttk.Entry(janela)
        entry_desc.insert(0, descricao_atual) 
        entry_desc.pack(pady=5, padx=20, fill='x')

        ttk.Label(janela, text="Valor (R$):").pack(pady=(10, 0), padx=20, fill='x')
        entry_valor = ttk.Entry(janela)
        entry_valor.insert(0, valor_atual_str) 
        entry_valor.pack(pady=5, padx=20, fill='x')

        ttk.Button(janela, text="Salvar Alterações", bootstyle="success",
                   command=lambda: self.salvar_edicao(janela, tipo_conta, tabela, lbl_total, lbl_divisao,
                                                      descricao_atual, data_atual,
                                                      entry_desc.get(), entry_valor.get())
                  ).pack(pady=20)

    def salvar_edicao(self, janela, tipo_conta, tabela, lbl_total, lbl_divisao,
                      descricao_antiga, data_antiga, nova_descricao, novo_valor_str):
        if not nova_descricao or not novo_valor_str:
            messagebox.showwarning("Aviso", "Preencha todos os campos!")
            return

        try:
            novo_valor = float(novo_valor_str.replace(',', '.'))
        except ValueError:
            messagebox.showerror("Erro", "Digite um valor numérico válido.")
            return

        conta_atualizada = {
            "descricao": nova_descricao,
            "valor": novo_valor,
            "usuario": self.usuario_logado,
            "data": datetime.now().strftime("%d/%m/%Y %H:%M")
        }

        # Envia a edição para a camada de dados
        self.db.editar_conta(self.mes_selecionado, tipo_conta, descricao_antiga, data_antiga, conta_atualizada)

        janela.destroy()
        self.carregar_dados_tabela(tipo_conta, tabela, lbl_total, lbl_divisao)

    # --- 5. PAINEL ADMIN ---
    def abrir_painel_admin(self):
        painel = ttk.Toplevel(self.root)
        painel.title("Painel do Administrador")
        painel.geometry("700x500")
        painel.grab_set()

        notebook_admin = ttk.Notebook(painel, bootstyle="warning")
        notebook_admin.pack(fill='both', expand=True, padx=10, pady=10)

        aba_usuarios = ttk.Frame(notebook_admin)
        aba_logs = ttk.Frame(notebook_admin)

        notebook_admin.add(aba_usuarios, text="Criar Novos Usuários")
        notebook_admin.add(aba_logs, text="Log Geral de Contas")

        # Aba Usuários
        ttk.Label(aba_usuarios, text="Cadastrar Novo Usuário", font=("Helvetica", 16, "bold")).pack(pady=20)
        
        frame_form = ttk.Frame(aba_usuarios)
        frame_form.pack()

        ttk.Label(frame_form, text="Nome de Usuário:").grid(row=0, column=0, pady=5, padx=5, sticky='e')
        entry_novo_user = ttk.Entry(frame_form)
        entry_novo_user.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(frame_form, text="Senha:").grid(row=1, column=0, pady=5, padx=5, sticky='e')
        entry_nova_senha = ttk.Entry(frame_form)
        entry_nova_senha.grid(row=1, column=1, pady=5, padx=5)

        ttk.Button(frame_form, text="Salvar Usuário", bootstyle="success",
                   command=lambda: self.salvar_novo_usuario(entry_novo_user, entry_nova_senha)
                  ).grid(row=2, columnspan=2, pady=20)

        # Aba Logs
        tabela_logs = ttk.Treeview(aba_logs, columns=("Mes", "Tipo", "Descricao", "Valor", "Usuario"), show="headings")
        tabela_logs.heading("Mes", text="Mês/Ano")
        tabela_logs.heading("Tipo", text="Tabela")
        tabela_logs.heading("Descricao", text="Descrição da Conta")
        tabela_logs.heading("Valor", text="Valor")
        tabela_logs.heading("Usuario", text="Criado Por")
        
        tabela_logs.column("Mes", width=100, anchor="center")
        tabela_logs.column("Tipo", width=120, anchor="center")
        tabela_logs.column("Descricao", width=200, anchor="w")
        tabela_logs.column("Valor", width=100, anchor="center")
        tabela_logs.column("Usuario", width=100, anchor="center")

        tabela_logs.pack(fill='both', expand=True, pady=10, padx=10)
        self.carregar_log_geral(tabela_logs)

    def salvar_novo_usuario(self, entry_user, entry_senha):
        novo_user = entry_user.get().strip()
        nova_senha = entry_senha.get().strip()

        if not novo_user or not nova_senha:
            messagebox.showwarning("Aviso", "Preencha usuário e senha!")
            return

        sucesso, mensagem = self.db.criar_usuario(novo_user, nova_senha)
        if sucesso:
            messagebox.showinfo("Sucesso", mensagem)
            entry_user.delete(0, 'end')
            entry_senha.delete(0, 'end')
        else:
            messagebox.showerror("Erro", mensagem)

    def carregar_log_geral(self, tabela):
        logs = self.db.obter_todos_logs()
        for mes_ano, tipo_conta, conta in logs:
            tabela.insert("", "end", values=(
                mes_ano, 
                tipo_conta, 
                conta['descricao'], 
                f"R$ {conta['valor']:.2f}", 
                conta['usuario']
            ))


if __name__ == "__main__":
    app = ttk.Window(themename="litera")
    GerenciadorContas(app)
    app.mainloop()