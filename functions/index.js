const functions = require("firebase-functions");
const admin = require("firebase-admin");
const {OpenAI} = require("openai");

admin.initializeApp();

// Initialize OpenAI
// IMPORTANTE: Configure sua API key nas variáveis de ambiente do Firebase:
// firebase functions:config:set openai.key="sua-api-key-aqui"
const openai = new OpenAI({
  apiKey: functions.config().openai?.key || process.env.OPENAI_API_KEY,
});

/**
 * Enhance text with AI
 */
exports.enhanceText = functions.https.onCall(async (data, context) => {
  const {context: textContext, text, instruction} = data;

  // Fallback if OpenAI is not configured
  if (!openai.apiKey) {
    console.warn("OpenAI API key not configured, returning original text");
    return {enhancedText: text};
  }

  try {
    const systemPrompt = `
Você é um assistente de narração para um jogo de mistério ambientado em uma estalagem antiga.
Seu trabalho é:
1. Enriquecer descrições com detalhes vívidos e sensoriais
2. Falar como os personagens de forma coerente com suas personalidades
3. Criar pequenos elementos narrativos que se encaixem no tema do jogo

Importante:
- Mantenha o tom de mistério e investigação
- Seja conciso mas detalhado
- Não mude fatos essenciais da história
- Não use marcações como asteriscos ou aspas, apenas texto puro
- Sempre responda em português brasileiro
- Nunca use palavras em inglês
`;

    const userPrompt = `
Contexto: ${textContext}

Texto original: ${text}

Instrução: ${instruction}

Responda apenas com o texto melhorado, em português brasileiro, sem comentários adicionais.
`;

    const completion = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: [
        {role: "system", content: systemPrompt},
        {role: "user", content: userPrompt},
      ],
      temperature: 0.7,
      max_tokens: 500,
    });

    const enhancedText = completion.choices[0]?.message?.content || text;

    return {enhancedText};
  } catch (error) {
    console.error("Error enhancing text:", error);
    // Return original text on error
    return {enhancedText: text};
  }
});

/**
 * Generate NPC dialogue
 */
exports.generateNPCDialogue = functions.https.onCall(async (data, context) => {
  const {character, characterLevel, question} = data;

  // Fallback if OpenAI is not configured
  if (!openai.apiKey) {
    console.warn("OpenAI API key not configured, returning default response");
    return {response: "Não consigo responder a isso no momento."};
  }

  try {
    const charName = character.name || "Personagem";
    const charPersonality = character.personality || "";

    // Get knowledge based on character level
    let knowledge = "";
    if (character.levels && character.levels.length > 0) {
      for (const level of character.levels) {
        if (level.level_number <= characterLevel) {
          knowledge += level.knowledge_scope + " ";
        }
      }
    }

    const systemPrompt = `
Você é ${charName}, um personagem em um jogo de mistério.

Sua personalidade: ${charPersonality}

O que você sabe (baseado no nível atual do jogador): ${knowledge}

Regras importantes:
1. Responda sempre em primeira pessoa como ${charName}
2. Seja fiel à sua personalidade
3. Só compartilhe informações que você conhece no nível atual
4. Mantenha respostas concisas (1-4 frases)
5. Use pulsação narrativa para incluir detalhe de linguagem corporal ou expressão.
6. Se a pergunta busca informações que você não deveria saber, demonstre confusão ou negue conhecimento
7. Sempre responda em português brasileiro
8. Nunca use palavras em inglês
`;

    const userPrompt = `
Um jogador perguntou: "${question}"

Como ${charName}, responda de acordo com seu conhecimento atual e personalidade.
Se a pergunta for sobre algo que você não deveria saber, demonstre confusão ou negue conhecimento de maneira natural.
`;

    const completion = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: [
        {role: "system", content: systemPrompt},
        {role: "user", content: userPrompt},
      ],
      temperature: 0.8,
      max_tokens: 300,
    });

    const response = completion.choices[0]?.message?.content || "Não sei o que dizer sobre isso.";

    return {response};
  } catch (error) {
    console.error("Error generating NPC dialogue:", error);
    return {response: "Não sei o que dizer sobre isso."};
  }
});

/**
 * Generate dynamic description
 */
exports.generateDynamicDescription = functions.https.onCall(async (data, context) => {
  const {locationName, areaName, baseDescription} = data;

  // Fallback if OpenAI is not configured
  if (!openai.apiKey) {
    console.warn("OpenAI API key not configured, returning base description");
    return {description: baseDescription};
  }

  try {
    const systemPrompt = `
Você é um narrador de um jogo de mistério ambientado em uma estalagem antiga.
Seu trabalho é criar descrições vívidas e atmosféricas dos ambientes que o jogador visita.

Importante:
- Crie descrições imersivas com detalhes sensoriais (visão, sons, cheiros, etc.)
- Mantenha o tom de mistério e suspense
- Adicione pequenos detalhes que não mudem a essência do local
- Não mencione personagens que não estejam explicitamente na descrição original
- Sempre responda em português brasileiro
- Nunca use palavras em inglês
`;

    const userPrompt = `
Local: ${locationName}
Área: ${areaName}

Descrição original: "${baseDescription}"

Crie uma descrição mais vívida e atmosférica deste ambiente, mantendo todos os elementos-chave,
mas adicionando detalhes sensoriais e elementos que aumentem a imersão.
Limite-se a 3-4 frases detalhadas. Responda em português brasileiro.
`;

    const completion = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: [
        {role: "system", content: systemPrompt},
        {role: "user", content: userPrompt},
      ],
      temperature: 0.7,
      max_tokens: 400,
    });

    const description = completion.choices[0]?.message?.content || baseDescription;

    return {description};
  } catch (error) {
    console.error("Error generating dynamic description:", error);
    return {description: baseDescription};
  }
});
