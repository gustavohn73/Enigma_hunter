# 🚀 Guia de Configuração - Enigma Hunter

## Sumário
- [Desenvolvimento Local (Emulators)](#desenvolvimento-local)
- [Deploy para Produção](#deploy-producao)
- [Solução de Problemas](#solucao-problemas)

---

## 📋 Pré-requisitos

```bash
# Node.js 18+
node --version

# Firebase CLI
npm install -g firebase-tools

# Verificar instalação
firebase --version
```

---

## 🔧 Desenvolvimento Local {#desenvolvimento-local}

### Passo 1: Instalar Dependências

```bash
# Na raiz do projeto
npm install

# Dependências das Functions
cd functions && npm install && cd ..
```

### Passo 2: Configurar Firebase

```bash
# Login no Firebase
firebase login

# Associar ao projeto (ou criar novo)
firebase use --add
# Selecione ou crie: "enigma-hunter"
```

### Passo 3: Iniciar Emulators

```bash
# Terminal 1 - Iniciar emulators
firebase emulators:start

# Aguarde até ver:
# ✔  All emulators ready!
# ┌─────────────┬────────────────┐
# │ Emulator    │ Host:Port      │
# ├─────────────┼────────────────┤
# │ Hosting     │ localhost:5000 │
# │ Firestore   │ localhost:8080 │
# │ Functions   │ localhost:5001 │
# └─────────────┴────────────────┘
```

### Passo 4: Upload dos Dados

```bash
# Terminal 2 - Upload dados para emulator
npm run upload-data

# Você verá:
# ✓ historia_base uploaded
# ✓ 12 ambientes uploaded
# ✓ 8 personagens uploaded
# ✓ All game data uploaded successfully!
```

### Passo 5: Acessar o Jogo

Abra: **http://localhost:5000**

✅ **Pronto!** Jogo funcionando localmente!

---

## 🚀 Deploy para Produção {#deploy-producao}

### Passo 1: Obter Credenciais do Firebase

#### 1.1 Configurar Web App
1. Firebase Console → Configurações do Projeto (⚙️)
2. Seus apps → Web (ícone `</>`)
3. Copie as configurações:

```javascript
{
  apiKey: "AIza...",
  authDomain: "enigma-hunter.firebaseapp.com",
  projectId: "enigma-hunter",
  // ...
}
```

4. Cole em `public/firebase-config.js` (linha 38-46)

#### 1.2 Obter Service Account Key
1. Firebase Console → Configurações → Contas de serviço
2. "Gerar nova chave privada"
3. Salvar como `service-account-key.json` na raiz do projeto

⚠️ **IMPORTANTE**: Adicione ao `.gitignore`:
```
service-account-key.json
```

### Passo 2: Upload dos Dados para Produção

```bash
# Executar upload em modo produção
npm run upload-data:production

# Confirme quando solicitado
# ✓ All game data uploaded to PRODUCTION!
```

### Passo 3: Deploy

```bash
# Deploy completo
npm run deploy

# OU deploy individual
npm run deploy:hosting     # Apenas frontend
npm run deploy:functions   # Apenas backend
```

### Passo 4: Verificar Deploy

```bash
# Após deploy bem-sucedido:
# ✔  Deploy complete!
# Hosting URL: https://enigma-hunter.web.app
```

Acesse a URL para jogar!

---

## ❓ Solução de Problemas {#solucao-problemas}

### Erro: "Cannot find module 'firebase-admin'"

**Causa**: Dependências não instaladas

**Solução**:
```bash
npm install
cd functions && npm install && cd ..
```

---

### Erro: "FIRESTORE_EMULATOR_HOST is set but..."

**Causa**: Emulators não estão rodando

**Solução**:
```bash
# Terminal 1
firebase emulators:start

# Terminal 2 (após emulators iniciarem)
npm run upload-data
```

---

### Erro: "Firebase not initialized"

**Causa**: Credenciais não configuradas em `firebase-config.js`

**Solução**: Configure credenciais do Firebase Console (ver [Passo 1.1](#passo-1-obter-credenciais-do-firebase))

---

### Dados não aparecem no jogo

**Desenvolvimento Local**:
```bash
# Verificar se emulators estão rodando
firebase emulators:start

# Re-executar upload
npm run upload-data
```

**Produção**:
```bash
# Verificar se dados foram enviados
npm run upload-data:production
```

Verificar no Firebase Console → Firestore Database → Collection `game_data`

---

### Emulators não iniciam

**Solução**:
```bash
# Limpar cache
firebase emulators:kill
rm -rf .firebase/

# Reiniciar
firebase emulators:start
```

---

## 🎯 Fluxo Recomendado

### Desenvolvimento

```bash
# 1. Iniciar emulators
firebase emulators:start

# 2. Upload dados (apenas primeira vez ou após mudanças)
npm run upload-data

# 3. Desenvolver
# Edite arquivos em public/
# Mudanças aparecem automaticamente em localhost:5000
```

### Deploy

```bash
# 1. Testar localmente
firebase emulators:start

# 2. Upload dados para produção
npm run upload-data:production

# 3. Deploy
npm run deploy

# 4. Verificar
# Acessar: https://enigma-hunter.web.app
```

---

## 📝 Comandos Úteis

```bash
# Desenvolvimento
npm run serve              # Alias para firebase emulators:start
npm run upload-data        # Upload para emulator
firebase emulators:kill    # Parar emulators

# Produção
npm run upload-data:production  # Upload para produção
npm run deploy                  # Deploy completo
npm run deploy:hosting          # Só frontend
npm run deploy:functions        # Só backend

# Debug
npm run logs               # Ver logs das functions
firebase emulators:clear   # Limpar cache
```

---

## 🔒 Segurança

### Nunca commite:
- `service-account-key.json`
- `functions/.env`
- Credenciais do Firebase

### Configure `.gitignore`:
```
service-account-key.json
.env
functions/.env
```

---

## 📚 Documentação Adicional

- [README_AI.md](README_AI.md) - Configuração de IA
- [SECURITY.md](SECURITY.md) - Práticas de segurança
- [README_FIREBASE.md](README_FIREBASE.md) - Detalhes técnicos

---

**Dúvidas?** Abra uma issue no repositório!
