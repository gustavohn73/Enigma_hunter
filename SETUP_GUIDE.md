# Guia Rápido de Configuração - Enigma Hunter Firebase

## ⚡ NOVO! Setup Ultra-Rápido com Gemini GRATUITO (3 minutos)

### Para 5 jogadores, use a API GRATUITA do Google!

```bash
# 1. Clone e instale
git clone [seu-repo]
cd Enigma_hunter
npm install && cd functions && npm install && cd ..

# 2. Inicie os emulators
firebase emulators:start

# 3. (Em outro terminal) Upload dos dados
npm run upload-data

# 4. Abra http://localhost:5000
```

**No jogo:**
1. Vá em "⚙️ Configurar IA"
2. Selecione "Google Gemini" (GRÁTIS!)
3. Cole sua API key (obtenha em: https://makersuite.google.com/app/apikey)
4. Teste e salve

✅ **Pronto!** Jogo funcionando com IA gratuita!

📖 **Quer gerar histórias próprias?** Clique em "✨ Criar Nova História (IA)"

---

## 🚀 Setup Completo (5 minutos)

### 1. Instalar Dependências

```bash
# Instalar Firebase CLI
npm install -g firebase-tools

# Instalar dependências do projeto
npm install

# Instalar dependências das Functions
cd functions && npm install && cd ..
```

### 2. Configurar Firebase

```bash
# Login no Firebase
firebase login

# Usar seu projeto (ou criar um novo)
firebase use --add

# Selecione ou crie o projeto "enigma-hunter"
```

### 3. Configurar Credenciais

#### a) Configurar Firebase no Frontend

1. Acesse [Firebase Console](https://console.firebase.google.com/)
2. Vá em **Configurações do Projeto** → **Seus apps** → **Web**
3. Copie as configurações
4. Edite `public/firebase-config.js` e cole suas configs

#### b) Configurar OpenAI API Key

**Obter API Key**:
- Acesse https://platform.openai.com/
- Crie uma conta
- Vá em "API Keys" e crie uma nova key
- Copie a key (começa com `sk-...`)

**Configurar para desenvolvimento local**:
```bash
cd functions
echo "OPENAI_API_KEY=sk-sua-key-aqui" > .env
cd ..
```

**Configurar para produção**:
```bash
firebase functions:config:set openai.key="sk-sua-key-aqui"
```

### 4. Iniciar Desenvolvimento Local

```bash
# Terminal 1: Iniciar emulators
firebase emulators:start

# Terminal 2: Upload dos dados do jogo (aguarde emulators iniciarem)
npm run upload-data
```

### 5. Acessar o Jogo

Abra seu navegador em: **http://localhost:5000**

🎮 **Pronto! O jogo está funcionando!**

---

## 📦 Deploy para Produção

### 1. Preparar Dados de Produção

Edite `upload-game-data.js` e desabilite o emulator:

```javascript
// Comente esta linha (linha ~30):
// process.env.FIRESTORE_EMULATOR_HOST = 'localhost:8080';
```

### 2. Obter Service Account Key

1. Firebase Console → **Configurações** → **Contas de serviço**
2. Clique em "Gerar nova chave privada"
3. Salve como `service-account-key.json` na raiz do projeto

Edite `upload-game-data.js` e descomente (linhas ~34-37):

```javascript
const serviceAccount = require('./service-account-key.json');
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});
```

### 3. Upload dos Dados

```bash
npm run upload-data
```

### 4. Deploy

```bash
# Deploy completo
npm run deploy

# Ou deploy individual
npm run deploy:hosting     # Apenas interface
npm run deploy:functions   # Apenas functions
```

### 5. Acessar Seu Jogo

Após o deploy, você verá a URL:
```
✔  Deploy complete!
Hosting URL: https://enigma-hunter.web.app
```

---

## ⚡ Comandos Úteis

```bash
# Desenvolvimento
npm run serve              # Inicia emulators
npm run upload-data        # Upload dados para Firestore

# Deploy
npm run deploy             # Deploy completo
npm run deploy:hosting     # Só frontend
npm run deploy:functions   # Só backend

# Logs e Debug
npm run logs               # Ver logs das functions
firebase emulators:kill    # Parar emulators
firebase emulators:clear   # Limpar cache
```

---

## ❓ Problemas Comuns

### "Firebase not initialized"
→ Configure `public/firebase-config.js` com suas credenciais

### "OpenAI API key not configured"
→ Crie arquivo `functions/.env` com sua API key

### "Permission denied"
→ Verifique `firestore.rules` ou use modo teste no Firestore

### Dados não aparecem
→ Execute `npm run upload-data` com emulators rodando

### Functions não funcionam
→ Verifique se está no plano Blaze do Firebase

---

## 📋 Checklist de Setup

- [ ] Firebase CLI instalado
- [ ] Projeto Firebase criado
- [ ] Firestore habilitado
- [ ] Credenciais configuradas em `firebase-config.js`
- [ ] OpenAI API key configurada
- [ ] Dependências instaladas (`npm install`)
- [ ] Emulators iniciados
- [ ] Dados carregados no Firestore
- [ ] Jogo acessível em localhost:5000

**Tudo marcado? Você está pronto! 🎉**

---

## 🆘 Precisa de Ajuda?

1. Consulte [README_FIREBASE.md](./README_FIREBASE.md) para documentação completa
2. Verifique os logs: `npm run logs`
3. Abra o console do navegador (F12) para ver erros JavaScript

**Boa investigação! 🔍**
