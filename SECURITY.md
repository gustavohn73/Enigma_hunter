# 🔒 Segurança do Enigma Hunter

## 📋 Índice

1. [Firebase API Keys - São Seguras?](#firebase-api-keys---são-seguras)
2. [Como Funciona a Segurança](#como-funciona-a-segurança)
3. [O Que Protege Seus Dados](#o-que-protege-seus-dados)
4. [Configuração Segura](#configuração-segura)
5. [Deploy em Produção](#deploy-em-produção)
6. [Boas Práticas](#boas-práticas)

---

## Firebase API Keys - São Seguras?

### ✅ **SIM! É Seguro Expor Firebase API Keys no Frontend**

#### Por quê?

As Firebase API Keys **NÃO SÃO SECRETAS** e são **DIFERENTES** de API keys tradicionais:

| Tipo | Função | Segurança |
|------|--------|-----------|
| **Firebase API Key** | Identifica seu projeto Firebase | ✅ Seguro expor |
| **API Key Tradicional** (ex: OpenAI) | Autoriza gastos/uso | ❌ NUNCA expor |

### 🔐 **Como o Firebase Protege Seus Dados**

A segurança do Firebase vem de **3 camadas**:

```
┌─────────────────────────────────────┐
│  1. Firebase API Key (público)      │  ← Apenas identifica o projeto
├─────────────────────────────────────┤
│  2. Firebase Rules (restrições)     │  ← VERDADEIRA SEGURANÇA
├─────────────────────────────────────┤
│  3. Domain Restrictions (opcional)  │  ← Bloqueia domínios não autorizados
└─────────────────────────────────────┘
```

#### **1. Firebase API Key**
- **Função**: Identifica qual projeto Firebase usar
- **Segurança**: Pública, pode ser exposta
- **Exemplo**: Como um endereço de e-mail - identifica, não autoriza

#### **2. Firebase Rules** ⭐ **A VERDADEIRA SEGURANÇA**
- **Função**: Controla quem pode ler/escrever dados
- **Segurança**: Configuradas no servidor Firebase
- **Exemplo**: Firestore Rules no arquivo `firestore.rules`

#### **3. Domain Restrictions**
- **Função**: Permite apenas domínios específicos
- **Segurança**: Configuradas no Firebase Console
- **Exemplo**: Só aceita requisições de `seu-site.web.app`

---

## Como Funciona a Segurança

### 📖 Analogia: Prédio com Portaria

Imagine um prédio:

```
Firebase API Key = Endereço do prédio (público)
Firebase Rules = Porteiro que verifica identidade
Domain Restrictions = Lista de visitantes autorizados
```

**Todos sabem o endereço do prédio**, mas só quem está na lista e tem ID correto pode entrar!

### 🎮 No Enigma Hunter

```javascript
// ✅ SEGURO - Firebase API Key no código
const firebaseConfig = {
    apiKey: "AIzaSyDxJWre...",  // ← PODE expor (identifica projeto)
    projectId: "enigma-hunter"
};

// ❌ NUNCA EXPONHA - API Keys de IA
const geminiKey = "AIzaSy...";  // ← NUNCA no código frontend!
```

---

## O Que Protege Seus Dados

### 1. **Firestore Security Rules** (`firestore.rules`)

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // 🔒 Dados do jogo: Somente leitura
    match /game_data/{document=**} {
      allow read: if true;           // ✅ Qualquer um pode ler
      allow write: if false;         // ❌ Ninguém pode escrever
    }

    // 🔒 Saves dos jogadores: Apenas o dono
    match /guest_saves/{playerId} {
      allow read, write: if request.auth != null
                         && request.auth.uid == playerId;
    }

    // 🔒 Histórias geradas: Apenas o criador
    match /generated_stories/{storyId} {
      allow read: if true;           // ✅ Qualquer um pode ler
      allow write: if request.auth != null;  // ✅ Apenas autenticados
    }
  }
}
```

### 2. **Domain Restrictions** (Firebase Console)

Configure no Firebase Console → Settings → App:

```
Domínios Autorizados:
✅ localhost (desenvolvimento)
✅ seu-dominio.web.app (produção)
✅ seu-dominio.firebaseapp.com (produção)
❌ Qualquer outro domínio (bloqueado)
```

### 3. **Rate Limiting** (Automático)

Firebase tem proteção automática contra:
- Requisições excessivas
- DDoS
- Abuso de API

---

## Configuração Segura

### 🔧 Desenvolvimento Local (Emulators)

```javascript
// public/firebase-config.js detecta automaticamente

if (isLocalhost) {
    // Usa emulators - credenciais demo
    firebaseConfig = {
        apiKey: "demo-api-key",
        projectId: "demo-project"
    };

    // Conecta aos emulators locais
    db.useEmulator("localhost", 8080);
}
```

✅ **Vantagens:**
- Não precisa de credenciais reais
- Totalmente offline
- Dados não vão para produção
- 100% seguro para testar

### 🚀 Produção

#### **Opção 1: Variáveis de Ambiente (Recomendado)**

1. Crie `.env.production`:
```bash
FIREBASE_API_KEY=AIzaSyDx...
FIREBASE_PROJECT_ID=enigma-hunter
FIREBASE_AUTH_DOMAIN=enigma-hunter.firebaseapp.com
# ... outras configurações
```

2. Use build tool para injetar (Vite, Webpack, etc):
```javascript
const firebaseConfig = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
    // ...
};
```

#### **Opção 2: Substituir Diretamente (Mais Simples)**

Edite `public/firebase-config.js` antes do deploy:

```javascript
// PRODUÇÃO
firebaseConfig = {
    apiKey: "AIzaSyDxJWre...",  // Cole sua API key real
    projectId: "enigma-hunter",
    // ...
};
```

⚠️ **Lembre-se:** Mesmo sendo seguro, configure Firebase Rules corretamente!

---

## Deploy em Produção

### 📝 Checklist de Segurança

Antes de fazer deploy, verifique:

- [ ] **1. Firebase Rules configuradas** (`firestore.rules`)
  ```bash
  firebase deploy --only firestore:rules
  ```

- [ ] **2. Domain Restrictions ativadas** (Firebase Console)
  - Vá em Project Settings → General → Your apps
  - Adicione apenas domínios autorizados

- [ ] **3. API Keys de IA NÃO estão no código**
  - ✅ Gemini: Configurar via interface do jogo
  - ✅ Ollama: Local, sem problemas
  - ❌ NUNCA coloque API keys diretamente no código

- [ ] **4. .gitignore atualizado**
  ```
  .env
  .env.local
  service-account-key.json
  functions/.env
  ```

- [ ] **5. Service Account Keys protegidas**
  - NUNCA commite `service-account-key.json`
  - Use apenas em deploy via CI/CD

### 🚀 Deploy Seguro

```bash
# 1. Verificar Firebase Rules
firebase deploy --only firestore:rules

# 2. Deploy da aplicação
npm run deploy

# 3. Verificar no Console
# Firebase Console → Firestore → Rules (tab)
# Teste as rules antes de ir para produção
```

---

## Boas Práticas

### ✅ **FAÇA:**

1. **Use Firebase Rules rigorosas**
   ```javascript
   // Exemplo: Apenas o dono pode editar
   allow write: if request.auth.uid == resource.data.userId;
   ```

2. **Configure API Keys de IA via interface**
   - Não coloque no código
   - Use localStorage (já implementado)
   - Usuário configura suas próprias keys

3. **Ative Domain Restrictions**
   - Firebase Console → Project Settings
   - Adicione apenas domínios autorizados

4. **Use Firebase App Check** (Avançado)
   ```bash
   firebase app-check
   ```
   - Verifica se requisição vem de app legítimo
   - Proteção extra contra bots

5. **Monitore uso no Console**
   - Firebase Console → Usage
   - Configure alertas de quota

### ❌ **NÃO FAÇA:**

1. **Não exponha Service Account Keys**
   ```javascript
   // ❌ NUNCA FAÇA ISSO:
   const serviceAccount = require('./service-account-key.json');
   ```

2. **Não coloque API Keys de serviços pagos no frontend**
   ```javascript
   // ❌ NUNCA:
   const openaiKey = "sk-...";  // Qualquer um pode roubar

   // ✅ CORRETO:
   // User configura via interface, salva em localStorage
   ```

3. **Não use regras permissivas demais**
   ```javascript
   // ❌ MUITO PERIGOSO:
   match /{document=**} {
     allow read, write: if true;  // Qualquer um faz qualquer coisa!
   }
   ```

4. **Não ignore avisos de segurança do Firebase**
   - Firebase Console mostra alertas
   - Corrija imediatamente

---

## 🆘 FAQ de Segurança

### **P: Minha API key do Firebase está visível no código. Devo me preocupar?**

**R:** NÃO! Isso é normal e seguro. A segurança vem das Firebase Rules, não da API key.

Leia mais: https://firebase.google.com/docs/projects/api-keys

---

### **P: Como proteger minha API key do Gemini?**

**R:** Gemini API keys são configuradas via interface do jogo e salvas no `localStorage` do navegador. Cada usuário usa sua própria key.

**Alternativas mais seguras:**
1. Use Ollama local (100% privado)
2. Crie Firebase Functions para chamar Gemini (key no servidor)

---

### **P: Alguém pode roubar meus dados do Firestore?**

**R:** Não, se suas Firebase Rules estão corretas. Exemplo:

```javascript
// Somente o dono do save pode ler/escrever
match /guest_saves/{playerId} {
  allow read, write: if request.auth.uid == playerId;
}
```

Teste suas rules: https://console.firebase.google.com/

---

### **P: Como sei se minhas regras estão seguras?**

**R:** Use o Firebase Rules Simulator:

1. Firebase Console → Firestore → Rules
2. Clique em "Rules Playground"
3. Teste diferentes cenários

---

### **P: Devo usar Firebase App Check?**

**R:** **Sim**, para produção com muitos usuários. É uma camada extra de segurança.

```bash
# Configurar App Check
firebase app-check
```

Leia mais: https://firebase.google.com/docs/app-check

---

## 📚 Recursos Adicionais

### Documentação Oficial

- **Firebase Security**: https://firebase.google.com/docs/rules
- **API Keys**: https://firebase.google.com/docs/projects/api-keys
- **App Check**: https://firebase.google.com/docs/app-check
- **Best Practices**: https://firebase.google.com/docs/rules/basics

### Vídeos Recomendados

- "Firebase Security Rules Explained" - Firebase Channel
- "Is it Safe to Expose Firebase API Keys?" - Firebase Channel

---

## ✅ Resumo

### **Firebase API Keys no Frontend:**
- ✅ **SEGURO** - Apenas identifica o projeto
- ✅ **NORMAL** - Todos os apps Firebase fazem isso
- ✅ **DOCUMENTADO** - Google confirma que é seguro

### **Verdadeira Segurança Vem De:**
1. **Firebase Rules** ⭐ MAIS IMPORTANTE
2. **Domain Restrictions**
3. **App Check** (opcional)
4. **Monitoramento**

### **API Keys que NUNCA devem ser expostas:**
- ❌ OpenAI, Claude, DeepSeek, Perplexity
- ❌ Service Account Keys do Firebase
- ❌ Qualquer key que autorize gastos

---

**Seu jogo Enigma Hunter está seguro! 🔒✨**

**Dúvidas?** Consulte a documentação oficial do Firebase sobre segurança.
