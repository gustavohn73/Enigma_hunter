# Sistema de IA Multi-Provider e Geração de Histórias

## 🤖 Visão Geral

O Enigma Hunter agora suporta **múltiplas APIs de IA** e possui um **gerador automático de histórias**! Você pode escolher entre várias opções, incluindo **APIs totalmente gratuitas**.

### ✨ Principais Recursos

1. **Multi-Provider de IA**: Escolha entre 6 provedores diferentes
2. **APIs Gratuitas Disponíveis**: Gemini (Google) e Ollama (local)
3. **Gerador de Histórias**: Crie mistérios personalizados com IA
4. **Configuração Simples**: Interface web para configurar tudo
5. **Sem Código Necessário**: Tudo via interface do jogo

---

## 🎯 Provedores de IA Disponíveis

### 🟢 **GRATUITOS** (Recomendado para 5 jogadores)

#### 1. **Google Gemini** ⭐ MELHOR OPÇÃO GRATUITA

- **API**: Totalmente gratuita
- **Limite**: 60 requisições/minuto
- **Qualidade**: Excelente (similar ao GPT-3.5)
- **Configuração**: Apenas API key
- **Custo**: $0/mês

**Como obter API key:**
1. Acesse: https://makersuite.google.com/app/apikey
2. Faça login com conta Google
3. Clique em "Create API Key"
4. Copie a chave

#### 2. **Ollama (Local)** ⭐ 100% GRATUITO

- **API**: Local (roda no seu computador)
- **Limite**: Ilimitado
- **Qualidade**: Depende do modelo (llama3 é ótimo)
- **Configuração**: Instalar aplicativo
- **Custo**: $0/mês (usa seu PC)

**Como instalar:**
1. Acesse: https://ollama.ai/download
2. Baixe e instale para seu sistema
3. Abra terminal e execute: `ollama run llama3`
4. Pronto! Ollama está rodando em http://localhost:11434

---

### 💰 **PAGOS** (Opcionais)

#### 3. **OpenAI GPT**
- **Modelo**: gpt-3.5-turbo ou gpt-4
- **Custo**: $0.002/1K tokens (GPT-3.5) | $0.03/1K tokens (GPT-4)
- **Estimativa**: ~$5-15/mês para 5 jogadores
- **Link**: https://platform.openai.com/api-keys

#### 4. **Anthropic Claude**
- **Modelo**: claude-3-haiku
- **Custo**: $0.25/1M tokens
- **Estimativa**: ~$3-10/mês para 5 jogadores
- **Link**: https://console.anthropic.com/account/keys

#### 5. **DeepSeek**
- **Modelo**: deepseek-chat
- **Custo**: Mais barato que OpenAI
- **Estimativa**: ~$2-8/mês para 5 jogadores
- **Link**: https://platform.deepseek.com/api_keys

#### 6. **Perplexity**
- **Modelo**: llama-3.1-sonar
- **Custo**: Similar ao OpenAI
- **Link**: https://www.perplexity.ai/settings/api

---

## 🚀 Configuração Rápida (Gemini - GRÁTIS)

### Passo 1: Obter API Key do Gemini

```bash
# 1. Acesse
https://makersuite.google.com/app/apikey

# 2. Faça login com sua conta Google

# 3. Clique em "Create API Key"

# 4. Copie a chave (começa com "AIza...")
```

### Passo 2: Configurar no Jogo

1. Abra o jogo: http://localhost:5000 (ou sua URL de produção)
2. No menu principal, clique em **"⚙️ Configurar IA"**
3. Selecione **"Google Gemini"** (tem selo GRÁTIS)
4. Cole sua API key no campo
5. Clique em **"Testar Conexão"** para verificar
6. Clique em **"Salvar"**

✅ Pronto! Você pode agora:
- Jogar o jogo com IA
- Gerar novas histórias

---

## 🎨 Gerador de Histórias

### Como Funciona

O gerador de histórias usa IA para criar **mistérios completamente novos** baseados nas suas preferências!

### Opções Disponíveis

#### **Tema**
- Medieval/Fantasia (tavernas, castelos)
- Moderno/Urbano (cidade contemporânea)
- Vitoriano (século XIX, Sherlock Holmes style)
- Ficção Científica (espaço, futuro)
- Personalizado (você descreve!)

#### **Classificação Etária**
- Infantil: Sem violência, mistério leve
- Adolescente: Mistério moderado
- Adulto: Temas mais sombrios e complexos

#### **Dificuldade**
- Fácil: 4 suspeitos, pistas óbvias
- Médio: 6 suspeitos, desafio moderado
- Difícil: 8+ suspeitos, muito complexo

#### **Duração**
- Curta: 30-45 minutos
- Média: 1-2 horas
- Longa: 2-4 horas

### Como Gerar uma História

1. No menu principal, clique em **"✨ Criar Nova História (IA)"**
2. Escolha as opções desejadas
3. Clique em **"✨ Gerar História"**
4. Aguarde (pode levar 1-2 minutos)
5. A IA vai criar:
   - História e introdução
   - Personagens suspeitos
   - Localizações para explorar
   - Objetos e pistas
   - Solução do mistério
6. O jogo inicia automaticamente com a nova história!

### O Que a IA Gera

A IA cria uma história completa incluindo:

- **Conceito**: Título, descrição, introdução narrativa
- **Crime**: Vítima, circunstâncias, método
- **Personagens**: 4-8 NPCs com personalidades únicas
  - Um culpado
  - Vários suspeitos
  - Motivos e segredos
  - Diálogos personalizados
- **Localizações**: 3-7 áreas para explorar
  - Múltiplas salas por localização
  - Detalhes e ambientação
  - Objetos escondidos
- **Pistas**: 8-15 evidências
  - Pistas-chave para resolver
  - Pistas secundárias
  - Documentos e objetos
- **Solução**: Critérios de resolução
  - Identidade do culpado
  - Motivo correto
  - Método usado

---

## 💡 Dicas para Melhor Experiência

### Para Gemini (Gratuito)

✅ **Vantagens:**
- Totalmente grátis
- 60 req/min (mais que suficiente)
- Qualidade excelente
- Sem configuração complexa

⚠️ **Limitações:**
- Requer internet
- Limite de 60 req/min (raramente atingido)

### Para Ollama (Local e Gratuito)

✅ **Vantagens:**
- 100% gratuito
- Privacidade total (tudo local)
- Sem limites de uso
- Funciona offline

⚠️ **Limitações:**
- Requer instalação
- Usa recursos do seu PC
- Pode ser mais lento
- Qualidade depende do modelo

**Modelos recomendados para Ollama:**
```bash
# Melhor equilíbrio qualidade/velocidade
ollama run llama3

# Mais rápido (menor qualidade)
ollama run phi3

# Melhor qualidade (mais lento)
ollama run llama3.1:70b
```

### Comparação de Custos (5 jogadores)

| Provider | Custo/Mês | Limite | Qualidade |
|----------|-----------|--------|-----------|
| **Gemini** | **$0** | 60 req/min | ⭐⭐⭐⭐⭐ |
| **Ollama** | **$0** | Ilimitado | ⭐⭐⭐⭐ |
| OpenAI | $5-15 | Pago por uso | ⭐⭐⭐⭐⭐ |
| Claude | $3-10 | Pago por uso | ⭐⭐⭐⭐⭐ |
| DeepSeek | $2-8 | Pago por uso | ⭐⭐⭐⭐ |
| Perplexity | $5-15 | Pago por uso | ⭐⭐⭐⭐ |

---

## 🔧 Troubleshooting

### Erro: "API key not configured"

**Solução:** Vá em "⚙️ Configurar IA" e configure sua API key.

### Erro: "Ollama not available"

**Solução:**
1. Certifique-se de que Ollama está instalado
2. Abra terminal e execute: `ollama serve`
3. Teste com: `curl http://localhost:11434`

### Erro: "Rate limit exceeded" (Gemini)

**Solução:**
- Você atingiu 60 req/min
- Aguarde 1 minuto
- Ou troque para Ollama (sem limites)

### Geração de história demora muito

**Normal!** A IA precisa criar:
- Conceito (10-20s)
- Personagens (30-40s)
- Localizações (20-30s)
- Objetos e pistas (30-40s)
- Solução (10-15s)

**Total**: 1-2 minutos é normal

**Dica:** Use Ollama local se tiver um PC potente (pode ser mais rápido).

### História gerada está incompleta

**Solução:**
1. Verifique sua API key
2. Tente novamente (pode ter sido erro temporário)
3. Tente com dificuldade "Fácil" primeiro
4. Se usar Ollama, tente modelo maior: `ollama run llama3.1`

---

## 📊 Estimativas de Uso

### Para 5 Jogadores

**Cenário 1: Gemini (Gratuito)**
- Custo: $0/mês
- Limite: 60 req/min
- Requisições/partida: ~50-100
- Partidas simultâneas possíveis: 30-60/min

**Cenário 2: Ollama (Gratuito)**
- Custo: $0/mês
- Limite: Ilimitado
- Hardware recomendado: 8GB RAM, GPU opcional
- Velocidade: Depende do PC

**Cenário 3: OpenAI GPT-3.5 (Pago)**
- Custo: ~$0.002/1K tokens
- Partida média: ~50K tokens
- Custo/partida: ~$0.10
- Custo/mês (5 jogadores, 4 partidas): ~$2-5

---

## 🎯 Recomendação Final

Para **5 jogadores**, a melhor opção é:

### **🥇 1ª Opção: Google Gemini**
- ✅ Totalmente gratuito
- ✅ Configuração simples
- ✅ Qualidade excelente
- ✅ Limite generoso (60 req/min)

### **🥈 2ª Opção: Ollama Local**
- ✅ 100% gratuito
- ✅ Privacidade total
- ✅ Sem limites
- ⚠️ Requer instalação

### Quando usar pagos?
- Apenas se precisar de features específicas
- Se quiser melhor qualidade absoluta (GPT-4)
- Se precisar de > 100 jogadores simultâneos

---

## 📝 Exemplos de Uso

### Exemplo 1: História Medieval para Crianças

```
Tema: Medieval/Fantasia
Classificação: Infantil
Dificuldade: Fácil
Duração: Curta

Resultado: História sobre um roubo de jóias na taverna do reino,
com 4 suspeitos amigáveis e pistas óbvias. Tempo: 30-45 min.
```

### Exemplo 2: Noir Complexo para Adultos

```
Tema: Vitoriano
Classificação: Adulto
Dificuldade: Difícil
Duração: Longa

Resultado: Mistério de assassinato na Londres vitoriana,
com 8 suspeitos complexos, múltiplos motivos e pistas enganosas.
Tempo: 2-4 horas.
```

### Exemplo 3: Sci-Fi para Adolescentes

```
Tema: Ficção Científica
Classificação: Adolescente
Dificuldade: Médio
Duração: Média

Resultado: Sabotagem em estação espacial,
com 6 tripulantes suspeitos e mistério moderado.
Tempo: 1-2 horas.
```

---

## 🔐 Privacidade e Segurança

### Dados Enviados para APIs

Quando você usa IA, os seguintes dados são enviados:
- Prompts de geração (conceitos, instruções)
- Texto do jogo (descrições, diálogos)
- **NÃO** são enviados: dados pessoais, saves, senhas

### Onde Ficam as API Keys

- Armazenadas **localmente** no navegador (localStorage)
- **Nunca** enviadas para o Firestore
- Acessíveis apenas por você

### Usando Ollama para Privacidade Total

Se privacidade é prioridade:
1. Use Ollama (tudo roda local)
2. Nenhum dado sai do seu computador
3. Funciona offline
4. 100% privado

---

## 🆘 Suporte

Problemas com IA?

1. **Verifique configuração**: "⚙️ Configurar IA" → "Testar Conexão"
2. **Console do navegador**: F12 para ver erros
3. **Troque de provider**: Gemini ↔ Ollama
4. **Consulte logs**: README_FIREBASE.md seção Troubleshooting

---

**Divirta-se criando mistérios infinitos! 🔍✨**
