# 🔧 Guia de Solução de Problemas

## Índice
- [Problemas de Inicialização](#problemas-inicializacao)
- [Problemas com Emulators](#problemas-emulators)
- [Problemas de Upload](#problemas-upload)
- [Problemas de Deploy](#problemas-deploy)
- [Problemas com Credenciais](#problemas-credenciais)

---

## Problemas de Inicialização {#problemas-inicializacao}

### ❌ "Cannot find module 'firebase-admin'"

**Sintoma**: Erro ao executar `npm run upload-data`

**Causa**: Dependências não instaladas

**Solução**:
```bash
npm install
cd functions && npm install && cd ..
```

---

### ❌ "Firebase Admin SDK error: credential is required"

**Sintoma**: Erro ao executar upload em modo produção

**Causa**: Arquivo `service-account-key.json` não encontrado

**Solução**:
1. Obtenha o arquivo no Firebase Console:
   - Configurações → Contas de serviço
   - "Gerar nova chave privada"
2. Salve como `service-account-key.json` na raiz do projeto

---

## Problemas com Emulators {#problemas-emulators}

### ❌ "Port 8080 is already in use"

**Sintoma**: Emulators não iniciam

**Causa**: Porta ocupada por outro processo

**Solução**:
```bash
# Linux/Mac
lsof -ti:8080 | xargs kill -9

# Windows
netstat -ano | findstr :8080
taskkill /PID [PID_NUMBER] /F

# Ou mude a porta em firebase.json
```

---

### ❌ "FIRESTORE_EMULATOR_HOST is set but emulator is not running"

**Sintoma**: Upload falha mesmo com configuração correta

**Causa**: Emulators não estão rodando

**Solução**:
```bash
# Terminal 1 - Iniciar emulators PRIMEIRO
firebase emulators:start

# Aguarde até ver: "All emulators ready!"

# Terminal 2 - Executar upload
npm run upload-data
```

---

### ❌ Emulators iniciam mas não aparecem dados

**Sintoma**: Localhost:5000 funciona mas não há dados do jogo

**Causa**: Upload não foi executado ou falhou

**Solução**:
```bash
# 1. Verificar se emulators estão rodando
# Deve mostrar "All emulators ready!"

# 2. Executar upload
npm run upload-data

# 3. Verificar se upload teve sucesso
# Deve mostrar: "✅ Todos os dados foram enviados com sucesso!"

# 4. Acessar Firestore UI
# http://localhost:4000/firestore
# Verificar se collection 'game_data' existe
```

---

## Problemas de Upload {#problemas-upload}

### ❌ "Error reading [...].json: ENOENT: no such file or directory"

**Sintoma**: Erro ao ler arquivos JSON

**Causa**: Estrutura de diretórios incorreta

**Solução**:
```bash
# Verificar estrutura esperada:
./historias/
  └── o_segredo_da_estalagem_do_cervo_negro/
      ├── historia_base.json
      ├── ambientes/
      │   └── *.json
      ├── personagens/
      │   └── *.json
      └── data/
          ├── objetos.json
          ├── pistas.json
          └── sistema-especializacao.json
```

---

### ❌ Upload demora muito ou trava

**Sintoma**: Script fica executando indefinidamente

**Causa**: 
1. Emulators não estão rodando
2. Problema de rede (produção)
3. Arquivo JSON corrompido

**Solução**:
```bash
# Para desenvolvimento
# 1. Verificar emulators
firebase emulators:start

# 2. Verificar logs
# Ctrl+C para cancelar
# Executar novamente com logs visíveis

# Para produção
# 1. Verificar conexão com internet
# 2. Verificar credenciais do Firebase
# 3. Verificar quotas no Firebase Console
```

---

## Problemas de Deploy {#problemas-deploy}

### ❌ "Error: HTTP Error: 403, The caller does not have permission"

**Sintoma**: Deploy falha com erro de permissão

**Causa**: Usuário sem permissão no projeto Firebase

**Solução**:
```bash
# 1. Verificar usuário logado
firebase login --reauth

# 2. Verificar projeto
firebase use

# 3. Se necessário, mudar projeto
firebase use --add
```

---

### ❌ "Error: Functions did not deploy properly"

**Sintoma**: Hosting funciona mas Functions não

**Causa**: 
1. Plano Spark (gratuito) não suporta Functions
2. Erro no código das Functions
3. Dependências não instaladas

**Solução**:
```bash
# 1. Verificar plano no Firebase Console
# Functions requerem plano Blaze (pay-as-you-go)

# 2. Instalar dependências
cd functions
npm install
cd ..

# 3. Testar Functions localmente
firebase emulators:start --only functions

# 4. Verificar logs
npm run logs
```

---

### ❌ Deploy funciona mas site não carrega

**Sintoma**: Deploy bem-sucedido mas site mostra erro

**Causa**: Credenciais do Firebase não configuradas

**Solução**:
1. Editar `public/firebase-config.js`
2. Substituir credenciais demo pelas reais:
```javascript
// Produção
firebaseConfig = {
    apiKey: "SUA_API_KEY_REAL",
    authDomain: "seu-projeto.firebaseapp.com",
    projectId: "seu-projeto",
    // ...
};
```

---

## Problemas com Credenciais {#problemas-credenciais}

### ❌ "Invalid API key"

**Sintoma**: Erro ao acessar Firestore no frontend

**Causa**: API key incorreta em `firebase-config.js`

**Solução**:
1. Firebase Console → Configurações → Seus apps
2. Copiar configuração correta
3. Colar em `public/firebase-config.js`

---

### ❌ "Permission denied" no Firestore

**Sintoma**: Erro ao ler/escrever dados

**Causa**: Firestore Rules muito restritivas

**Solução**:
```javascript
// firestore.rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Para desenvolvimento/teste
    match /{document=**} {
      allow read, write: if true;
    }
    
    // Para produção (após testar)
    match /game_data/{document=**} {
      allow read: if true;
      allow write: if false;
    }
  }
}
```

Deploy das rules:
```bash
firebase deploy --only firestore:rules
```

---

## Problemas Gerais

### ❌ Console do navegador mostra erro

**Solução**:
1. Pressione F12 para abrir DevTools
2. Vá na aba "Console"
3. Copie a mensagem de erro
4. Busque neste documento ou pesquise online

---

### ❌ Nada funciona

**Reset Completo**:
```bash
# 1. Limpar tudo
firebase emulators:kill
rm -rf .firebase/
rm -rf node_modules/
rm -rf functions/node_modules/

# 2. Reinstalar
npm install
cd functions && npm install && cd ..

# 3. Reiniciar emulators
firebase emulators:start

# 4. Re-upload dados
npm run upload-data
```

---

## 📞 Obter Ajuda

Se o problema persistir:

1. **Verificar logs**:
   ```bash
   npm run logs
   ```

2. **Verificar console do Firebase**:
   https://console.firebase.google.com/

3. **Abrir issue no GitHub**:
   Inclua:
   - Descrição do problema
   - Mensagens de erro completas
   - Passos para reproduzir
   - Sistema operacional
   - Versão do Node.js

---

## 📋 Checklist de Diagnóstico

Antes de pedir ajuda, verifique:

- [ ] Node.js 18+ instalado
- [ ] Firebase CLI instalado e atualizado
- [ ] Dependências instaladas (`npm install`)
- [ ] Emulators rodando (desenvolvimento)
- [ ] Service account key configurado (produção)
- [ ] Credenciais em firebase-config.js corretas
- [ ] Estrutura de diretórios correta
- [ ] Console do navegador sem erros
- [ ] Firestore Rules configuradas
- [ ] Plano Blaze ativo (se usar Functions)

---

**Boa sorte! 🍀**
