# Enigma Hunter - Firebase Web Version

Versão web do jogo **O Segredo da Estalagem do Cervo Negro** usando Firebase.

## 📋 Visão Geral

Este projeto converte o jogo de investigação baseado em Python/CLI para uma aplicação web completa usando:

- **Firebase Hosting**: Hospedagem da interface web
- **Firebase Firestore**: Banco de dados NoSQL para dados do jogo e saves
- **Firebase Functions**: Lógica do servidor e integração com IA
- **OpenAI API**: Geração de conteúdo dinâmico (substitui Ollama)

## 🏗️ Estrutura do Projeto

```
Enigma_hunter/
├── public/                          # Arquivos web (hospedados no Firebase Hosting)
│   ├── index.html                  # Interface principal do jogo
│   ├── styles.css                  # Estilos (tema medieval/mistério)
│   ├── firebase-config.js          # Configuração do Firebase
│   ├── game-engine.js              # Motor do jogo
│   └── game.js                     # Controlador de UI
├── functions/                       # Firebase Functions
│   ├── index.js                    # Cloud Functions (IA)
│   ├── package.json                # Dependencies
│   └── .eslintrc.js                # ESLint config
├── historias/                       # Dados do jogo (JSON)
│   └── o_segredo_da_estalagem_do_cervo_negro/
│       ├── historia_base.json      # História principal
│       ├── ambientes/              # Localizações
│       ├── personagens/            # NPCs
│       └── data/                   # Objetos, pistas, etc.
├── firebase.json                    # Configuração do Firebase
├── firestore.rules                  # Regras de segurança
├── firestore.indexes.json           # Índices do Firestore
├── .firebaserc                      # Projeto Firebase
└── upload-game-data.js              # Script para upload de dados
```

## 🚀 Configuração Inicial

### 1. Pré-requisitos

```bash
# Node.js 18 ou superior
node --version

# NPM
npm --version

# Firebase CLI
npm install -g firebase-tools
```

### 2. Criar Projeto no Firebase Console

1. Acesse [Firebase Console](https://console.firebase.google.com/)
2. Clique em "Adicionar projeto"
3. Nome do projeto: `enigma-hunter` (ou outro de sua escolha)
4. Habilite Google Analytics (opcional)
5. Crie o projeto

### 3. Habilitar Serviços no Firebase

No console do Firebase, habilite:

#### Firestore Database
1. Vá em **Build > Firestore Database**
2. Clique em "Criar banco de dados"
3. Escolha modo: **Teste** (para desenvolvimento) ou **Produção**
4. Escolha localização: `southamerica-east1` (São Paulo)
5. Clique em "Ativar"

#### Firebase Hosting
1. Vá em **Build > Hosting**
2. Clique em "Começar"
3. Siga as instruções

#### Functions (opcional para desenvolvimento local)
1. Vá em **Build > Functions**
2. Faça upgrade para plano **Blaze** (pay-as-you-go)
   - **Nota**: Plano gratuito não permite chamadas externas (OpenAI API)

### 4. Configurar Firebase no Projeto

```bash
# Login no Firebase
firebase login

# Inicializar projeto (se ainda não foi feito)
cd Enigma_hunter
firebase init

# Selecione:
# - Firestore
# - Functions
# - Hosting
# - Emulators (opcional, mas recomendado)
```

**IMPORTANTE**: Use os arquivos já criados quando perguntado:
- `firebase.json` → já existe
- `firestore.rules` → já existe
- `public/index.html` → já existe
- `functions/index.js` → já existe

### 5. Configurar Credenciais do Firebase

Edite `public/firebase-config.js` e substitua as configurações:

```javascript
const firebaseConfig = {
    apiKey: "SUA_API_KEY",
    authDomain: "SEU_PROJECT_ID.firebaseapp.com",
    projectId: "SEU_PROJECT_ID",
    storageBucket: "SEU_PROJECT_ID.appspot.com",
    messagingSenderId: "SEU_MESSAGING_SENDER_ID",
    appId: "SEU_APP_ID"
};
```

Para obter essas configurações:
1. No Firebase Console, vá em **Configurações do Projeto** (⚙️)
2. Role até "Seus apps"
3. Clique em "Web" (ícone `</>`)
4. Registre o app e copie as configurações

### 6. Configurar API Key da OpenAI

#### Para Desenvolvimento Local (Emulators):
```bash
# Crie arquivo .env no diretório functions/
cd functions
echo "OPENAI_API_KEY=sk-sua-api-key-aqui" > .env
```

#### Para Produção:
```bash
# Configure variável de ambiente no Firebase
firebase functions:config:set openai.key="sk-sua-api-key-aqui"
```

Para obter uma API key da OpenAI:
1. Acesse [platform.openai.com](https://platform.openai.com/)
2. Crie uma conta ou faça login
3. Vá em **API Keys**
4. Clique em "Create new secret key"
5. Copie a chave (você só verá uma vez!)

### 7. Instalar Dependências

```bash
# Dependências das Functions
cd functions
npm install

# Dependências do script de upload
cd ..
npm install firebase-admin
```

## 🧪 Desenvolvimento Local (Emuladores)

### 1. Iniciar Emuladores

```bash
# Inicie todos os emuladores
firebase emulators:start

# Ou apenas alguns específicos
firebase emulators:start --only hosting,firestore,functions
```

Você verá:
- **Hosting**: http://localhost:5000
- **Firestore UI**: http://localhost:4000
- **Functions**: http://localhost:5001

### 2. Upload dos Dados do Jogo

```bash
# Certifique-se de que os emuladores estão rodando!
node upload-game-data.js
```

Isso irá:
- Ler todos os arquivos JSON de `historias/`
- Fazer upload para o Firestore (emulador local)
- Criar a collection `game_data` com todos os documentos

### 3. Testar o Jogo

Abra http://localhost:5000 no navegador e teste:
- Criar novo jogo
- Explorar ambientes
- Conversar com personagens (requer OpenAI API key)
- Salvar/Carregar jogo
- Fazer acusação

## 📦 Deploy para Produção

### 1. Upload de Dados para Produção

Edite `upload-game-data.js` e comente as linhas do emulator:

```javascript
// Comente esta linha:
// process.env.FIRESTORE_EMULATOR_HOST = 'localhost:8080';

// Descomente e configure service account:
// const serviceAccount = require('./service-account-key.json');
// admin.initializeApp({
//   credential: admin.credential.cert(serviceAccount)
// });
```

Para obter service account key:
1. Firebase Console → **Configurações do Projeto** → **Contas de serviço**
2. Clique em "Gerar nova chave privada"
3. Salve o arquivo como `service-account-key.json`

```bash
# Execute o upload
node upload-game-data.js
```

### 2. Deploy do Projeto

```bash
# Deploy completo (Hosting + Functions + Firestore rules)
firebase deploy

# Ou deploy individual
firebase deploy --only hosting
firebase deploy --only functions
firebase deploy --only firestore:rules
```

### 3. Verificar Deploy

Após o deploy, você verá:
```
✔  Deploy complete!

Project Console: https://console.firebase.google.com/project/enigma-hunter/overview
Hosting URL: https://enigma-hunter.web.app
```

Acesse a **Hosting URL** para jogar!

## 🎮 Como Jogar

### Interface Web

1. **Menu Principal**:
   - Novo Jogo: Cria um novo save
   - Carregar Jogo: Lista saves existentes
   - Instruções: Tutorial completo

2. **Tela de Jogo**:
   - **Painel Principal**: Narrativa e opções de exploração
   - **Painel Lateral**:
     - 🎒 Inventário: Objetos coletados
     - 🔍 Pistas: Evidências descobertas
     - ⚡ Habilidades: Progressão das skills
     - 💾 Salvar: Salva o jogo
     - ⚖️ Acusação: Resolver o mistério

3. **Exploração**:
   - Clique nas opções para explorar detalhes
   - Examine objetos para coletar evidências
   - Mova-se entre áreas conectadas

4. **Conversas**:
   - Clique em personagens para iniciar diálogo
   - Digite perguntas livres (IA gera respostas)
   - Palavras-chave especiais desbloqueiam segredos

5. **Sistema de Habilidades**:
   - 5 habilidades evoluem conforme você joga
   - Habilidades desbloqueiam novas opções
   - Verifique seu progresso no painel de skills

## 🔧 Configurações Avançadas

### Customizar Modelo de IA

Edite `functions/index.js` para usar modelos diferentes:

```javascript
// Trocar de gpt-3.5-turbo para gpt-4
const completion = await openai.chat.completions.create({
  model: "gpt-4",  // ou "gpt-4-turbo-preview"
  // ...
});
```

### Ajustar Temperatura da IA

```javascript
// Mais criativo (0.8-1.0)
temperature: 1.0,

// Mais consistente (0.5-0.7)
temperature: 0.6,

// Muito determinístico (0.0-0.3)
temperature: 0.2,
```

### Regras de Segurança do Firestore

Edite `firestore.rules` para ajustar permissões:

```javascript
// Permitir apenas usuários autenticados
match /guest_saves/{sessionId} {
  allow read, write: if request.auth != null;
}

// Limitar tamanho de saves
match /guest_saves/{sessionId} {
  allow write: if request.resource.size() < 1024 * 1024; // 1MB max
}
```

## 🐛 Troubleshooting

### Erro: "Firebase not initialized"

**Solução**: Verifique se `firebase-config.js` tem as configurações corretas do seu projeto.

### Erro: "OpenAI API key not configured"

**Solução**:
- Local: Crie arquivo `.env` em `functions/` com `OPENAI_API_KEY`
- Produção: Execute `firebase functions:config:set openai.key="sua-key"`

### Erro: "Permission denied" no Firestore

**Solução**: Verifique `firestore.rules`. Para testes, você pode temporariamente usar:

```javascript
match /{document=**} {
  allow read, write: if true; // ⚠️ APENAS PARA TESTES!
}
```

### Jogo não carrega dados

**Solução**:
1. Verifique se executou `upload-game-data.js`
2. No Firebase Console, vá em Firestore e confira se a collection `game_data` existe
3. Abra o console do navegador (F12) e veja erros

### Functions retornam erro 401/403

**Solução**:
- Certifique-se de estar no plano Blaze do Firebase
- Verifique se a API key da OpenAI é válida
- Confira se configurou: `firebase functions:config:set openai.key="..."`

### Emulators não iniciam

**Solução**:
```bash
# Pare processos anteriores
firebase emulators:kill

# Limpe cache
firebase emulators:clear

# Inicie novamente
firebase emulators:start
```

## 📊 Custos Estimados

### Firebase (Plano Gratuito Spark)
- Firestore: 50K reads/day, 20K writes/day
- Hosting: 10GB storage, 360MB/day transfer
- ⚠️ **Functions não disponíveis** no plano gratuito

### Firebase (Plano Blaze - Pay as You Go)
- Firestore: Gratuito até os limites do Spark
- Hosting: Gratuito até os limites do Spark
- Functions: $0.40/milhão de invocações + $0.0000025/GB-segundo
- **Estimativa**: ~$5-10/mês para uso moderado (100 jogadores)

### OpenAI API
- GPT-3.5-turbo: $0.0015/1K tokens (~$0.002/conversa)
- GPT-4: $0.03/1K tokens (~$0.05/conversa)
- **Estimativa**: $5-20/mês dependendo do uso

**Total Estimado**: $10-30/mês para ~100 jogadores ativos

## 🎯 Próximos Passos

### Melhorias Sugeridas

1. **Autenticação**:
   - Adicionar Firebase Auth
   - Login com Google/Email
   - Múltiplos saves por usuário

2. **Multiplayer**:
   - Compartilhar descobertas entre jogadores
   - Leaderboard global
   - Estatísticas de resolução

3. **Mais Histórias**:
   - Adicionar novas investigações
   - Sistema de DLC
   - Editor de histórias

4. **Melhorias de UI**:
   - Animações e transições
   - Sons ambiente
   - Tema escuro/claro

5. **Mobile**:
   - PWA (Progressive Web App)
   - App nativo com Capacitor

## 📝 Licença e Créditos

- **Jogo Original**: Enigma Hunter
- **Conversão Firebase**: [Seu Nome]
- **IA**: OpenAI GPT-3.5-turbo
- **Fontes**: Google Fonts (Cinzel, Crimson Text)

## 🤝 Suporte

Para dúvidas ou problemas:
1. Verifique a seção [Troubleshooting](#-troubleshooting)
2. Confira os logs do Firebase: `firebase functions:log`
3. Abra uma issue no repositório

---

**Divirta-se investigando o mistério! 🔍🕵️**
