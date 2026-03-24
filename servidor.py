import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="API Contas em Dia (Firebase)")

# ==========================================
# CONEXÃO COM O FIREBASE
# ==========================================
# Lê o arquivo de chaves que você baixou
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# --- MODELOS DE DADOS ---
class Credenciais(BaseModel):
    usuario: str
    senha: str

class NovaPlanilha(BaseModel):
    chave_mes: str

class Conta(BaseModel):
    descricao: str
    valor: float
    usuario: str
    data: str
    vencimento: str = ""        # NOVO: Guarda a data de validade
    status: str = "PENDENTE"    # NOVO: PENDENTE ou PAGO

class EdicaoConta(BaseModel):
    descricao_antiga: str
    data_antiga: str
    conta_atualizada: Conta

# No Firebase não precisamos inicializar arquivos, nós inicializamos o usuário admin se não existir
def garantir_admin():
    doc_admin = db.collection('usuarios').document('admin').get()
    if not doc_admin.exists:
        db.collection('usuarios').document('admin').set({'senha': 'admin'})

garantir_admin()

# ==========================================
# ENDPOINTS (As "Portas" da nossa API)
# ==========================================

# 1. Sistema de Login e Usuários
@app.post("/login")
def validar_login(cred: Credenciais):
    doc = db.collection('usuarios').document(cred.usuario).get()
    if doc.exists and doc.to_dict().get('senha') == cred.senha:
        return {"sucesso": True}
    raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")

@app.post("/usuarios")
def criar_usuario(cred: Credenciais):
    doc_ref = db.collection('usuarios').document(cred.usuario)
    if doc_ref.get().exists:
        raise HTTPException(status_code=400, detail="Esse usuário já existe!")
    
    doc_ref.set({'senha': cred.senha})
    return {"sucesso": True, "mensagem": "Usuário criado com sucesso!"}

# 2. Gerenciamento de Meses
@app.get("/meses")
def obter_meses_existentes():
    meses = [doc.id for doc in db.collection('contas').stream()]
    return {"meses": meses}

@app.post("/meses")
def criar_mes(planilha: NovaPlanilha):
    doc_ref = db.collection('contas').document(planilha.chave_mes)
    if doc_ref.get().exists:
        raise HTTPException(status_code=400, detail="Mês já existe")
        
    doc_ref.set({"fixas": [], "temporarias": [], "divisao": []})
    return {"sucesso": True}

# 3. Gerenciamento de Contas (CRUD)
@app.get("/contas/{mes_ano}/{tipo_conta}")
def obter_contas(mes_ano: str, tipo_conta: str, usuario: str = Query(None)): # NOVO: Recebe quem está a pedir
    doc = db.collection('contas').document(mes_ano).get()
    if doc.exists:
        dados = doc.to_dict()
        contas = dados.get(tipo_conta, [])
        
        # FILTRO DE PRIVACIDADE: Se for a aba pessoal, devolve só as do próprio utilizador
        if tipo_conta == "pessoal" and usuario:
            contas = [c for c in contas if c.get('usuario') == usuario]
            
        return {"contas": contas}
    return {"contas": []}

@app.post("/contas/{mes_ano}/{tipo_conta}")
def adicionar_conta(mes_ano: str, tipo_conta: str, conta: Conta):
    doc_ref = db.collection('contas').document(mes_ano)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Mês não encontrado")
        
    dados = doc.to_dict()
    # Se a lista ainda não existir (ex: meses antigos), cria agora
    if tipo_conta not in dados:
        dados[tipo_conta] = []
        
    dados[tipo_conta].append(conta.model_dump())
    doc_ref.set(dados)
    return {"sucesso": True}

@app.put("/contas/{mes_ano}/{tipo_conta}")
def editar_conta(mes_ano: str, tipo_conta: str, edicao: EdicaoConta):
    doc_ref = db.collection('contas').document(mes_ano)
    doc = doc_ref.get()
    
    dados = doc.to_dict()
    contas = dados.get(tipo_conta, [])
    
    for i, c in enumerate(contas):
        if c['descricao'] == edicao.descricao_antiga and c['data'] == edicao.data_antiga:
            contas[i] = edicao.conta_atualizada.model_dump()
            dados[tipo_conta] = contas
            doc_ref.set(dados)
            return {"sucesso": True}
            
    raise HTTPException(status_code=404, detail="Conta original não encontrada")

@app.delete("/contas/{mes_ano}/{tipo_conta}")
def remover_conta(mes_ano: str, tipo_conta: str, descricao: str = Query(...), data: str = Query(...)):
    doc_ref = db.collection('contas').document(mes_ano)
    doc = doc_ref.get()
    
    dados = doc.to_dict()
    contas = dados.get(tipo_conta, [])
    
    for i, c in enumerate(contas):
        if c['descricao'] == descricao and c['data'] == data:
            del contas[i]
            dados[tipo_conta] = contas
            doc_ref.set(dados)
            return {"sucesso": True}
            
    raise HTTPException(status_code=404, detail="Conta não encontrada")
# 4. Logs Gerais
@app.get("/logs")
def obter_todos_logs():
    logs = []
    meses = db.collection('contas').stream()
    
    for doc in meses:
        mes_ano = doc.id
        dados = doc.to_dict()
        for tipo_conta, contas in dados.items():
            for conta in contas:
                logs.append({
                    "mes_ano": mes_ano, 
                    "tipo_conta": tipo_conta.upper(), 
                    "conta": conta
                })
    return {"logs": logs}