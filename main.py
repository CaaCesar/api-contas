from datetime import datetime
from tkinter import messagebox

import json
import os
import calendar
import ttkbootstrap as ttk
import requests
import threading

# =====================================================================
# CAMADA DE DADOS (Conectada ao FastAPI)
# =====================================================================
class ControladorDeDados:
    def __init__(self):
        # Endereço onde o seu servidor FastAPI está rodando
        self.api_url = 'https://api-contas-4uei.onrender.com'
        
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

    def obter_contas(self, mes_ano, tipo_conta, usuario_logado):
        try:
            # timeout=15 impede o aplicativo de carregar para sempre!
            resposta = requests.get(
                f"{self.api_url}/contas/{mes_ano}/{tipo_conta}?usuario={usuario_logado}", 
                timeout=15 
            )
            if resposta.status_code == 200:
                return resposta.json().get("contas", [])
            else:
                print(f"Erro no servidor. Código: {resposta.status_code}")
                return []
        except requests.exceptions.Timeout:
            print("O servidor demorou muito a responder (Timeout).")
            raise Exception("Servidor demorou muito.")
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão: {e}")
            raise Exception("Sem conexão.")
    
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
        
        # Salvamos o botão em uma variável (self.btn_login) para podermos alterá-lo
        self.btn_login = ttk.Button(frame_centro, text="Entrar", command=self.fazer_login, bootstyle="success")
        self.btn_login.pack(pady=20, fill='x')

    def fazer_login(self):
        usuario = self.entry_usuario.get().strip()
        senha = self.entry_senha.get().strip()
        
        # Feedback visual imediato e bloqueio de múltiplos cliques
        self.btn_login.config(text="Entrando... Aguarde", state="disabled")
        
        def tarefa_login():
            try:
                if self.db.validar_login(usuario, senha):
                    self.usuario_logado = usuario 
                    self.root.after(0, self.construir_tela_meses)
                else:
                    self.root.after(0, lambda: messagebox.showerror("Erro", "Usuário ou senha incorretos."))
                    self.root.after(0, lambda: self.btn_login.config(text="Entrar", state="normal"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro no sistema: {e}"))
                self.root.after(0, lambda: self.btn_login.config(text="Entrar", state="normal"))

        # Inicia a thread
        threading.Thread(target=tarefa_login).start()

# --- 2. TELA DE MESES ---
    def construir_tela_meses(self, mensagem_status="", tipo_status="success"):
        self.limpar_tela()
        
        ttk.Label(self.frame_atual, text="Selecione o Mês / Ano", font=("Helvetica", 22, "bold")).pack(pady=(10, 10))
        
        if self.usuario_logado == "admin":
            ttk.Button(self.frame_atual, text="⚙️ Painel Administrador", bootstyle="warning", 
                       command=self.abrir_painel_admin).pack(pady=(0, 20))
        
        # Label temporária de carregamento
        lbl_carregando = ttk.Label(self.frame_atual, text="Buscando planilhas na nuvem...", font=("Helvetica", 12, "italic"))
        lbl_carregando.pack(pady=20)

        # Rodapé de mensagens
        frame_rodape = ttk.Frame(self.frame_atual)
        frame_rodape.pack(side='bottom', fill='x', pady=10)
        self.lbl_status = ttk.Label(frame_rodape, text=mensagem_status, font=("Helvetica", 11), bootstyle=tipo_status)
        self.lbl_status.pack()

        if mensagem_status:
            self.root.after(4000, lambda: self.lbl_status.config(text="") if self.lbl_status.winfo_exists() else None)

        def tarefa_buscar_meses():
            try:
                meses_criados = self.db.obter_meses_existentes()
                self.root.after(0, lambda: desenhar_botoes(meses_criados))
            except Exception:
                self.root.after(0, lambda: lbl_carregando.config(text="Erro ao conectar com a nuvem.", bootstyle="danger"))

        def desenhar_botoes(meses_criados):
            lbl_carregando.destroy() # Some com o texto de carregamento
            
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

        threading.Thread(target=tarefa_buscar_meses).start()

    def criar_novo_mes(self, chave_mes):
        self.lbl_status.config(text="Criando mês na nuvem...", bootstyle="info")
        
        def tarefa_criar():
            try:
                self.db.criar_mes(chave_mes)
                self.root.after(0, lambda: self.construir_tela_meses(f"Planilha de {chave_mes} criada com sucesso!", "success"))
            except Exception as e:
                self.root.after(0, lambda: self.construir_tela_meses(f"Erro ao criar planilha: {e}", "danger"))
                
        threading.Thread(target=tarefa_criar).start()
    
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
        
        # NOVO: Aba Pessoal
        self.aba_pessoal = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_pessoal, text="Conta Pessoal 🔒")
        
        self.construir_interface_aba(self.aba_fixas, "fixas")
        self.construir_interface_aba(self.aba_temporarias, "temporarias")
        self.construir_interface_aba(self.aba_divisao, "divisao")
        self.construir_interface_aba(self.aba_pessoal, "pessoal") # Constrói a aba nova

    def construir_interface_aba(self, parent, tipo_conta):
        frame_botoes = ttk.Frame(parent)
        frame_botoes.pack(fill='x', pady=5)
        
        frame_borda = ttk.Frame(parent, bootstyle="dark", padding=1)
        frame_borda.pack(fill='both', expand=True, pady=10)
        
        # Adicionamos as colunas Vencimento e Status
        tabela = ttk.Treeview(frame_borda, columns=("Nome", "Valor", "Vencimento", "Status", "Usuario", "Data"), show="headings")
        tabela.pack(fill='both', expand=True)

        tabela.column("Nome", anchor="w", width=200)
        tabela.column("Valor", anchor="center", width=100)
        tabela.column("Vencimento", anchor="center", width=100)
        tabela.column("Status", anchor="center", width=100)
        tabela.column("Usuario", anchor="center", width=100)
        tabela.column("Data", anchor="center", width=120)
        
        tabela.heading("Nome", text="Descrição")
        tabela.heading("Valor", text="Valor (R$)")
        tabela.heading("Vencimento", text="Vencimento")
        tabela.heading("Status", text="Status")
        tabela.heading("Usuario", text="Criado Por")
        tabela.heading("Data", text="Data/Hora")
        
        # Configurando as cores das linhas
        tabela.tag_configure('pago', foreground='green')
        tabela.tag_configure('atrasado', foreground='red', font=('Helvetica', 10, 'bold'))

        frame_resultados = ttk.Frame(parent)
        frame_resultados.pack(fill='x', pady=10)
        
        lbl_total = ttk.Label(frame_resultados, text="Total: R$ 0.00", font=("Helvetica", 14, "bold"))
        lbl_total.pack(side='left', padx=20)
        
        lbl_divisao = ttk.Label(frame_resultados, text="Por pessoa (Divisão por 3): R$ 0.00", font=("Helvetica", 14))
        lbl_divisao.pack(side='left')

        # Novos Botões
        ttk.Button(frame_botoes, text="+ Adicionar", bootstyle="primary", 
                   command=lambda tc=tipo_conta, tab=tabela, lt=lbl_total, ld=lbl_divisao: self.abrir_janela_adicao(tc, tab, lt, ld)).pack(side='left', padx=5)
        
        ttk.Button(frame_botoes, text="Editar", bootstyle="secondary",
                   command=lambda tc=tipo_conta, tab=tabela, lt=lbl_total, ld=lbl_divisao: self.abrir_janela_edicao(tc, tab, lt, ld)).pack(side='left', padx=5)
                   
        ttk.Button(frame_botoes, text="- Remover", bootstyle="danger",
                   command=lambda tc=tipo_conta, tab=tabela, lt=lbl_total, ld=lbl_divisao: self.remover_conta(tc, tab, lt, ld)).pack(side='left', padx=5)

        # BOTÃO NOVO: Alternar entre PAGO e PENDENTE
        ttk.Button(frame_botoes, text="✔ Marcar Pago/Pendente", bootstyle="success",
                   command=lambda tc=tipo_conta, tab=tabela, lt=lbl_total, ld=lbl_divisao: self.alternar_status_conta(tc, tab, lt, ld)).pack(side='right', padx=5)
        
        self.carregar_dados_tabela(tipo_conta, tabela, lbl_total, lbl_divisao)

    def carregar_dados_tabela(self, tipo_conta, tabela, lbl_total, lbl_divisao):
        for item in tabela.get_children():
            tabela.delete(item)
            
        lbl_total.config(text="Buscando dados da nuvem...")
        lbl_divisao.config(text="Aguarde...")

        def tarefa_em_segundo_plano():
            try:
                contas = self.db.obter_contas(self.mes_selecionado, tipo_conta, self.usuario_logado)
                self.root.after(0, lambda: atualizar_interface(contas))
            except Exception as e:
                # ISTO VAI SALVAR A NOSSA VIDA! Vai imprimir o erro real na tela preta do terminal.
                print(f"ERRO AO CARREGAR TABELA {tipo_conta}: {e}") 
                self.root.after(0, lambda: lbl_total.config(text="Erro ao ligar à nuvem."))
                self.root.after(0, lambda: lbl_divisao.config(text="Tente novamente."))

        def atualizar_interface(contas):
            soma_total = 0.0
            hoje = datetime.now().date() 

            for conta in contas:
                # ... (resto do código do for loop mantém-se igual) ...
                status_exibicao = conta.get('status', 'PENDENTE')
                vencimento_str = conta.get('vencimento', '')

                if status_exibicao == 'PENDENTE' and vencimento_str:
                    try:
                        data_venc = datetime.strptime(vencimento_str, "%d/%m/%Y").date()
                        if data_venc < hoje:
                            status_exibicao = "ATRASADO"
                    except ValueError:
                        pass 

                item_id = tabela.insert("", "end", values=(
                    conta['descricao'], 
                    f"R$ {conta['valor']:.2f}", 
                    vencimento_str,
                    status_exibicao,
                    conta['usuario'], 
                    conta['data']
                ))

                if status_exibicao == "PAGO":
                    tabela.item(item_id, tags=('pago',))
                elif status_exibicao == "ATRASADO":
                    tabela.item(item_id, tags=('atrasado',))

                if status_exibicao != "PAGO":
                    soma_total += float(conta['valor'])
                
            lbl_total.config(text=f"Falta Pagar: R$ {soma_total:.2f}")
            
            # Lógica para não mostrar divisão na conta pessoal
            if tipo_conta == "pessoal":
                lbl_divisao.config(text="Apenas visualização privada.")
            else:
                lbl_divisao.config(text=f"Por pessoa: R$ {(soma_total / 3):.2f}")

    def abrir_janela_adicao(self, tipo_conta, tabela, lbl_total, lbl_divisao):
        janela = ttk.Toplevel(self.root)
        janela.title("Adicionar Conta")
        janela.geometry("350x350")
        janela.grab_set() 
        
        ttk.Label(janela, text="Descrição:").pack(pady=(10, 0), padx=20, fill='x')
        entry_desc = ttk.Entry(janela)
        entry_desc.pack(pady=5, padx=20, fill='x')
        
        ttk.Label(janela, text="Valor (R$):").pack(pady=(10, 0), padx=20, fill='x')
        entry_valor = ttk.Entry(janela)
        entry_valor.pack(pady=5, padx=20, fill='x')

        # NOVO: Widget de Calendário!
        ttk.Label(janela, text="Vencimento:").pack(pady=(10, 0), padx=20, fill='x')
        # dateformat="%d/%m/%Y" garante que a data saia no formato brasileiro
        entry_vencimento = ttk.DateEntry(janela, dateformat="%d/%m/%Y", bootstyle="primary")
        entry_vencimento.pack(pady=5, padx=20, fill='x')
        
        ttk.Button(janela, text="Salvar", bootstyle="success", 
                   # entry_vencimento.entry.get() puxa o texto de dentro do calendário
                   command=lambda: self.salvar_nova_conta(janela, tipo_conta, tabela, entry_desc.get(), entry_valor.get(), entry_vencimento.entry.get(), lbl_total, lbl_divisao)
                  ).pack(pady=20)
        
    def salvar_nova_conta(self, janela, tipo_conta, tabela, descricao, valor_str, vencimento_str, lbl_total, lbl_divisao):
        if not descricao or not valor_str:
            messagebox.showwarning("Aviso", "Preencha os campos principais!")
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
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "vencimento": vencimento_str,
            "status": "PENDENTE"
        }

        janela.destroy()
        lbl_total.config(text="Salvando na nuvem...")

        def tarefa_salvar():
            try:
                self.db.adicionar_conta(self.mes_selecionado, tipo_conta, nova_conta)
                self.root.after(0, lambda: self.carregar_dados_tabela(tipo_conta, tabela, lbl_total, lbl_divisao))
            except Exception:
                self.root.after(0, lambda: messagebox.showerror("Erro", "Falha ao salvar na nuvem!"))

        threading.Thread(target=tarefa_salvar).start()

    def remover_conta(self, tipo_conta, tabela, lbl_total, lbl_divisao):
        selecionado = tabela.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione uma conta na tabela para remover!")
            return

        # AS COLUNAS MUDARAM DE POSIÇÃO!
        # 0: Nome | 1: Valor | 2: Vencimento | 3: Status | 4: Usuario | 5: Data
        valores = tabela.item(selecionado[0], 'values')
        descricao_alvo = valores[0]
        criador_da_conta = valores[4] # Agora é o 4 (antes era o 2)
        data_alvo = valores[5]        # Agora é o 5 (antes era o 3)

        if self.usuario_logado != "admin" and self.usuario_logado != criador_da_conta:
            messagebox.showerror("Acesso Negado", "Você só tem permissão para apagar contas que você mesmo criou!")
            return

        resposta = messagebox.askyesno("Confirmar", f"Tem certeza que deseja remover a conta '{descricao_alvo}'?")
        if not resposta:
            return

        # Feedback visual
        lbl_total.config(text="Removendo da nuvem...")

        def tarefa_remover():
            try:
                self.db.remover_conta(self.mes_selecionado, tipo_conta, descricao_alvo, data_alvo)
                self.root.after(0, lambda: self.carregar_dados_tabela(tipo_conta, tabela, lbl_total, lbl_divisao))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erro", "Falha ao remover na nuvem!"))
                self.root.after(0, lambda: self.carregar_dados_tabela(tipo_conta, tabela, lbl_total, lbl_divisao))

        threading.Thread(target=tarefa_remover).start()

    def abrir_janela_edicao(self, tipo_conta, tabela, lbl_total, lbl_divisao):
        selecionado = tabela.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione uma conta na tabela para editar!")
            return

        # Agora a nossa tabela tem 6 colunas, precisamos de capturar todas na ordem correta
        valores = tabela.item(selecionado[0], 'values')
        descricao_atual = valores[0]
        valor_atual_str = valores[1].replace('R$ ', '') 
        vencimento_atual = valores[2]   # Coluna nova
        status_atual = valores[3]       # Coluna nova
        criador_da_conta = valores[4]
        data_atual = valores[5]

        # Trava de segurança
        if self.usuario_logado != "admin" and self.usuario_logado != criador_da_conta:
            messagebox.showerror("Acesso Negado", "Só tem permissão para editar contas que o próprio criou!")
            return

        janela = ttk.Toplevel(self.root)
        janela.title("Editar Conta")
        janela.geometry("350x350")
        janela.grab_set()

        ttk.Label(janela, text="Descrição:").pack(pady=(10, 0), padx=20, fill='x')
        entry_desc = ttk.Entry(janela)
        entry_desc.insert(0, descricao_atual) 
        entry_desc.pack(pady=5, padx=20, fill='x')

        ttk.Label(janela, text="Valor (R$):").pack(pady=(10, 0), padx=20, fill='x')
        entry_valor = ttk.Entry(janela)
        entry_valor.insert(0, valor_atual_str) 
        entry_valor.pack(pady=5, padx=20, fill='x')

        # NOVO: Adiciona o calendário na janela de edição
        ttk.Label(janela, text="Vencimento:").pack(pady=(10, 0), padx=20, fill='x')
        entry_vencimento = ttk.DateEntry(janela, dateformat="%d/%m/%Y", bootstyle="primary")
        entry_vencimento.pack(pady=5, padx=20, fill='x')
        
        # Preenche o calendário com a data que já estava guardada na conta
        if vencimento_atual:
            entry_vencimento.entry.delete(0, 'end')
            entry_vencimento.entry.insert(0, vencimento_atual)

        ttk.Button(janela, text="Guardar Alterações", bootstyle="success",
                   command=lambda: self.salvar_edicao(janela, tipo_conta, tabela, lbl_total, lbl_divisao,
                                                      descricao_atual, data_atual,
                                                      entry_desc.get(), entry_valor.get(), 
                                                      entry_vencimento.entry.get(), status_atual) # Passamos o vencimento e o status
                  ).pack(pady=20)

    def salvar_edicao(self, janela, tipo_conta, tabela, lbl_total, lbl_divisao,
                      descricao_antiga, data_antiga, nova_descricao, novo_valor_str, novo_vencimento, status_atual):
        if not nova_descricao or not novo_valor_str:
            messagebox.showwarning("Aviso", "Preencha os campos principais!")
            return

        try:
            novo_valor = float(novo_valor_str.replace(',', '.'))
        except ValueError:
            messagebox.showerror("Erro", "Digite um valor numérico válido.")
            return

        # Montamos o dicionário atualizado com os novos campos
        conta_atualizada = {
            "descricao": nova_descricao,
            "valor": novo_valor,
            "usuario": self.usuario_logado,
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "vencimento": novo_vencimento,
            "status": status_atual # Mantém o estado que já estava (PAGO, PENDENTE, etc.)
        }

        janela.destroy()
        lbl_total.config(text="A guardar edição na nuvem...")

        def tarefa_editar():
            try:
                self.db.editar_conta(self.mes_selecionado, tipo_conta, descricao_antiga, data_antiga, conta_atualizada)
                self.root.after(0, lambda: self.carregar_dados_tabela(tipo_conta, tabela, lbl_total, lbl_divisao))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erro", "Falha ao editar na nuvem!"))
                self.root.after(0, lambda: self.carregar_dados_tabela(tipo_conta, tabela, lbl_total, lbl_divisao))

        threading.Thread(target=tarefa_editar).start()
    
    
    
    
    
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
                   command=lambda: self.salvar_novo_usuario(entry_novo_user, entry_nova_senha, btn_salvar)
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

    def salvar_novo_usuario(self, entry_user, entry_senha, btn_salvar):
        novo_user = entry_user.get().strip()
        nova_senha = entry_senha.get().strip()

        if not novo_user or not nova_senha:
            messagebox.showwarning("Aviso", "Preencha usuário e senha!")
            return

        btn_salvar.config(text="Salvando...", state="disabled")

        def tarefa_criar_usuario():
            sucesso, mensagem = self.db.criar_usuario(novo_user, nova_senha)
            
            def finalizar():
                btn_salvar.config(text="Salvar Usuário", state="normal")
                if sucesso:
                    messagebox.showinfo("Sucesso", mensagem)
                    entry_user.delete(0, 'end')
                    entry_senha.delete(0, 'end')
                else:
                    messagebox.showerror("Erro", mensagem)
                    
            self.root.after(0, finalizar)

        threading.Thread(target=tarefa_criar_usuario).start()

    def carregar_log_geral(self, tabela):
        # Insere uma linha temporária para mostrar carregamento
        tabela.insert("", "end", iid="loading", values=("Buscando...", "Aguarde", "Carregando logs da nuvem", "", ""))

        def tarefa_carregar_logs():
            try:
                logs = self.db.obter_todos_logs()
                self.root.after(0, lambda: desenhar_logs(logs))
            except Exception:
                self.root.after(0, lambda: tabela.item("loading", values=("Erro", "", "Falha de conexão", "", "")))

        def desenhar_logs(logs):
            tabela.delete("loading")
            for mes_ano, tipo_conta, conta in logs:
                tabela.insert("", "end", values=(
                    mes_ano, 
                    tipo_conta, 
                    conta['descricao'], 
                    f"R$ {conta['valor']:.2f}", 
                    conta['usuario']
                ))

        threading.Thread(target=tarefa_carregar_logs).start()

    def alternar_status_conta(self, tipo_conta, tabela, lbl_total, lbl_divisao):
        selecionado = tabela.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione uma conta para alterar o status!")
            return

        valores = tabela.item(selecionado[0], 'values')
        descricao_alvo = valores[0]
        valor_str = valores[1].replace('R$ ', '')
        vencimento_atual = valores[2]
        status_atual = valores[3]
        criador_da_conta = valores[4]
        data_alvo = valores[5]

        # Trava de segurança
        if self.usuario_logado != "admin" and self.usuario_logado != criador_da_conta:
            messagebox.showerror("Acesso Negado", "Você só pode alterar o status de contas que você criou!")
            return

        # Lógica de inversão
        novo_status = "PAGO" if status_atual in ["PENDENTE", "ATRASADO"] else "PENDENTE"

        conta_atualizada = {
            "descricao": descricao_alvo,
            "valor": float(valor_str),
            "usuario": criador_da_conta, # Mantém o criador original
            "data": data_alvo,           # Mantém a data original para não quebrar a ID
            "vencimento": vencimento_atual,
            "status": novo_status
        }

        lbl_total.config(text="Atualizando status...")

        def tarefa_status():
            try:
                self.db.editar_conta(self.mes_selecionado, tipo_conta, descricao_alvo, data_alvo, conta_atualizada)
                self.root.after(0, lambda: self.carregar_dados_tabela(tipo_conta, tabela, lbl_total, lbl_divisao))
            except Exception:
                self.root.after(0, lambda: messagebox.showerror("Erro", "Falha ao atualizar status na nuvem!"))
                self.root.after(0, lambda: self.carregar_dados_tabela(tipo_conta, tabela, lbl_total, lbl_divisao))

        threading.Thread(target=tarefa_status).start()


if __name__ == "__main__":
    app = ttk.Window(themename="litera")
    GerenciadorContas(app)
    app.mainloop()