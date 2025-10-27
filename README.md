# 🔍 Enigma Hunter

**Jogo de investigação e mistério baseado em texto com IA generativa**

> Crie e jogue histórias de mistério personalizadas usando inteligência artificial!

[![Firebase](https://img.shields.io/badge/Firebase-Hosting-orange)](https://firebase.google.com/)
[![Gemini](https://img.shields.io/badge/Google-Gemini-blue)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## ✨ Recursos Principais

🎮 **Jogo Web Completo**
- Interface moderna e responsiva
- Jogue de qualquer dispositivo
- Sistema de save/load na nuvem
- Totalmente em português

🤖 **IA Generativa Multi-Provider**
- **GRATUITO**: Google Gemini (60 req/min)
- **GRATUITO**: Ollama local (ilimitado)
- Suporte a OpenAI, Claude, DeepSeek, Perplexity
- Configuração via interface web

✨ **Gerador de Histórias com IA**
- Crie mistérios personalizados
- Escolha tema, dificuldade e duração
- Personagens e pistas gerados automaticamente
- Histórias infinitas!

🕵️ **Sistema de Investigação**
- Explore ambientes detalhados
- Colete evidências e pistas
- Interrogue personagens com diálogos de IA
- 5 habilidades de investigação
- Resolva o mistério!

---

## 🚀 Quick Start (3 minutos)

### 1. Instalar Dependências

```bash
npm install -g firebase-tools
npm install
cd functions && npm install && cd ..
```

### 2. Obter API Key do Gemini (GRÁTIS)

1. Acesse: https://makersuite.google.com/app/apikey
2. Faça login com conta Google
3. Clique em "Create API Key"
4. Copie a chave

### 3. Iniciar Localmente

```bash
# Terminal 1: Iniciar emulators
firebase emulators:start

# Terminal 2: Upload dados do jogo
npm run upload-data
```

### 4. Jogar!

1. Abra: **http://localhost:5000**
2. Vá em "⚙️ Configurar IA"
3. Selecione "Google Gemini"
4. Cole sua API key
5. Clique em "Testar Conexão" → "Salvar"

✅ **Pronto! Divirta-se!**

---

## 📖 Documentação

- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Guia rápido de configuração
- **[README_AI.md](README_AI.md)** - Tudo sobre IA e geração de histórias
- **[README_FIREBASE.md](README_FIREBASE.md)** - Deploy e configurações avançadas

---

## 🎨 Como Criar uma História Personalizada

1. No menu, clique em **"✨ Criar Nova História (IA)"**
2. Escolha suas preferências:
   - **Tema**: Medieval, Moderno, Vitoriano, Sci-Fi, Personalizado
   - **Classificação**: Infantil, Adolescente, Adulto
   - **Dificuldade**: Fácil (4 suspeitos), Médio (6), Difícil (8+)
   - **Duração**: Curta (30min), Média (1-2h), Longa (2-4h)
3. Clique em **"✨ Gerar História"**
4. Aguarde 1-2 minutos
5. Jogue o mistério criado!

### Exemplo de História Gerada

```
Tema: Ficção Científica
Classificação: Adolescente
Dificuldade: Médio
Duração: Média (1-2h)

Resultado:
📖 "Sabotagem na Estação Orbital Kepler"
👥 6 tripulantes suspeitos
🏢 5 setores da estação
🔍 12 pistas técnicas
🎯 Culpado: Engenheiro chefe
⏱️ Tempo: ~1.5 horas
```

---

## 🏗️ Estrutura do Projeto

```
Enigma_hunter/
├── public/                    # Frontend (hospedado no Firebase Hosting)
│   ├── index.html            # Interface principal
│   ├── styles.css            # Tema medieval/mistério
│   ├── firebase-config.js    # Configuração Firebase
│   ├── ai-providers.js       # Sistema multi-provider de IA
│   ├── story-generator.js    # Gerador de histórias
│   ├── game-engine.js        # Motor do jogo
│   └── game.js               # Controlador de UI
├── functions/                 # Backend (Firebase Functions)
│   └── index.js              # (Opcional - pode usar IA direto no cliente)
├── historias/                 # Dados do jogo original
│   └── o_segredo_da_estalagem_do_cervo_negro/
├── firebase.json             # Configuração Firebase
├── package.json              # Dependências
└── upload-game-data.js       # Script para upload de dados
```

---

## 💰 Custos (para 5 jogadores)

| Provider | Custo/Mês | Limite | Recomendação |
|----------|-----------|--------|--------------|
| **Google Gemini** ⭐ | **$0** | 60 req/min | **RECOMENDADO** |
| **Ollama (Local)** | **$0** | Ilimitado | Privacidade total |
| OpenAI GPT-3.5 | ~$5-15 | Pago por uso | Se precisar GPT-4 |
| Claude | ~$3-10 | Pago por uso | Alternativa |

**Para 5 jogadores:** Use **Gemini gratuitamente!**

---

## 🔧 Comandos Úteis

```bash
# Desenvolvimento Local
npm run serve              # Inicia emulators
npm run upload-data        # Upload dados para Firestore

# Deploy para Produção
npm run deploy             # Deploy completo
npm run deploy:hosting     # Só frontend
npm run deploy:functions   # Só backend

# Logs e Debug
npm run logs               # Ver logs das functions
firebase emulators:kill    # Parar emulators
```

---

## 🎯 Recursos do Jogo

### Sistema de Investigação
- 🗺️ Explore múltiplas localizações
- 🔍 Examine objetos e colete evidências
- 💬 Interrogue NPCs com IA
- 📚 Descubra pistas escondidas
- ⚡ Desenvolva habilidades especializadas

### Sistema de IA
- 🤖 Diálogos dinâmicos com NPCs
- 📝 Descrições enriquecidas de ambientes
- ✨ Geração de histórias completas
- 🎭 Personalidades únicas de personagens
- 🧠 Respostas contextuais inteligentes

### Sistema de Progressão
- 📊 5 habilidades de investigação
- 🎓 Níveis de relacionamento com NPCs
- 🔓 Conteúdo desbloqueável
- 💾 Saves automáticos
- 🏆 Sistema de pontuação

---

## 🆘 Troubleshooting

### Erro: "Firebase SDK not loaded"

**Solução:** Limpe o cache do navegador (Ctrl+Shift+Delete) e recarregue.

### Erro: "API key not configured"

**Solução:** Vá em "⚙️ Configurar IA" e configure sua API key do Gemini.

### Erro: "Cannot read properties of undefined"

**Solução:**
1. Verifique se Firebase está configurado em `public/firebase-config.js`
2. Para emuladores locais, use as configurações padrão (já configurado)

### Geração de história muito lenta

**Solução:**
- Normal: 1-2 minutos
- Use Ollama local para mais velocidade (se tiver PC potente)
- Comece com dificuldade "Fácil" para testes

---

## 📚 Mais Informações

### Configurar IA
Consulte **[README_AI.md](README_AI.md)** para:
- Escolher o melhor provider
- Obter API keys gratuitas
- Configurar Ollama local
- Usar o gerador de histórias
- Troubleshooting de IA

### Deploy para Produção
Consulte **[README_FIREBASE.md](README_FIREBASE.md)** para:
- Criar projeto no Firebase
- Configurar Firebase Hosting
- Deploy de Functions
- Configurações de segurança
- Monitoramento e logs

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para:

1. Fazer fork do projeto
2. Criar uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abrir um Pull Request

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 🎮 Divirta-se!

Criado com ❤️ usando Firebase, Google Gemini AI e muita imaginação!

**Boa investigação, detetive! 🔍✨**
