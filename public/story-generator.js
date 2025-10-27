// Story Generator - Cria histórias de mistério com IA
class StoryGenerator {
    constructor(aiProvider) {
        this.aiProvider = aiProvider;
    }

    // Gera uma história completa baseada nas preferências do usuário
    async generateStory(preferences) {
        const {
            theme,           // ex: "medieval", "modern", "sci-fi", "victorian"
            ageRating,       // ex: "child", "teen", "adult"
            difficulty,      // ex: "easy", "medium", "hard"
            duration,        // ex: "short", "medium", "long"
            customTheme      // tema personalizado do usuário
        } = preferences;

        console.log('Generating story with preferences:', preferences);

        try {
            // Etapa 1: Gerar conceito básico da história
            const concept = await this.generateConcept(theme, ageRating, customTheme);

            // Etapa 2: Gerar personagens
            const characters = await this.generateCharacters(concept, ageRating, difficulty);

            // Etapa 3: Gerar localizações
            const locations = await this.generateLocations(concept, duration);

            // Etapa 4: Gerar objetos e pistas
            const {objects, clues} = await this.generateObjectsAndClues(
                concept,
                characters,
                locations,
                difficulty
            );

            // Etapa 5: Gerar solução do mistério
            const solution = await this.generateSolution(
                concept,
                characters,
                objects,
                clues
            );

            // Montar estrutura final
            const story = this.assembleStory({
                concept,
                characters,
                locations,
                objects,
                clues,
                solution
            });

            return story;

        } catch (error) {
            console.error('Error generating story:', error);
            throw error;
        }
    }

    async generateConcept(theme, ageRating, customTheme) {
        const themeDescriptions = {
            medieval: 'uma taverna medieval em uma cidade de fantasia',
            modern: 'um ambiente moderno urbano',
            'sci-fi': 'uma estação espacial futurista',
            victorian: 'a Londres vitoriana do século XIX',
            custom: customTheme || 'um ambiente de mistério'
        };

        const ageGuidelines = {
            child: 'adequado para crianças, sem violência explícita',
            teen: 'adequado para adolescentes, mistério moderado',
            adult: 'pode incluir temas mais sombrios e complexos'
        };

        const systemPrompt = `Você é um mestre em criar histórias de mistério interativas.
Sempre responda em português brasileiro, com estrutura JSON válida.`;

        const prompt = `Crie um conceito de história de mistério ambientado em ${themeDescriptions[theme]}.
A história deve ser ${ageGuidelines[ageRating]}.

Gere um JSON com:
{
  "title": "Título da história",
  "description": "Descrição breve (2-3 frases)",
  "introduction": "Introdução imersiva (4-5 parágrafos)",
  "crime": {
    "victim": "Nome da vítima",
    "victimDescription": "Descrição da vítima",
    "apparentCause": "Causa aparente da morte",
    "trueCause": "Causa real da morte",
    "criminalMethod": "Método usado pelo criminoso"
  },
  "setting": {
    "era": "Época/era da história",
    "mainLocation": "Local principal",
    "atmosphere": "Atmosfera geral"
  }
}

Responda APENAS com o JSON válido, sem texto adicional.`;

        const response = await this.aiProvider.generateText(prompt, systemPrompt, {
            temperature: 0.8,
            maxTokens: 2000
        });

        return this.parseJSON(response);
    }

    async generateCharacters(concept, ageRating, difficulty) {
        const numCharacters = difficulty === 'easy' ? 4 : difficulty === 'medium' ? 6 : 8;

        const systemPrompt = `Você é um criador de personagens para histórias de mistério.
Sempre responda em português brasileiro, com JSON válido.`;

        const prompt = `Baseado nesta história: "${concept.title}"
Crime: ${concept.crime.victim} foi morto(a). Causa aparente: ${concept.crime.apparentCause}

Crie ${numCharacters} personagens suspeitos (incluindo 1 culpado).
Cada personagem deve ter:
- Personalidade única
- Motivo para estar no local
- Possível motivo para o crime (mesmo os inocentes)
- Segredos e informações que revelam gradualmente

Retorne JSON array:
[
  {
    "character_id": 1,
    "name": "Nome",
    "age": idade,
    "occupation": "Profissão",
    "personality": "Descrição da personalidade",
    "appearance": "Aparência física",
    "base_description": "Descrição inicial",
    "is_culprit": false,
    "motive": "Motivo aparente",
    "secret": "Segredo que escondem",
    "area_id": 1,
    "levels": [
      {
        "level_number": 0,
        "narrative_stance": "Como se comportam inicialmente",
        "knowledge_scope": "O que sabem e compartilham neste nível",
        "is_defensive": false,
        "triggers": []
      }
    ]
  }
]

UM personagem deve ter "is_culprit": true.
Responda APENAS com o JSON válido.`;

        const response = await this.aiProvider.generateText(prompt, systemPrompt, {
            temperature: 0.9,
            maxTokens: 3000
        });

        return this.parseJSON(response);
    }

    async generateLocations(concept, duration) {
        const numLocations = duration === 'short' ? 3 : duration === 'medium' ? 5 : 7;

        const systemPrompt = `Você é um designer de ambientes para jogos de mistério.
Sempre responda em português brasileiro, com JSON válido.`;

        const prompt = `Crie ${numLocations} localizações para a história "${concept.title}"
Ambientada em: ${concept.setting.mainLocation}

Cada localização deve ter múltiplas áreas para explorar e detalhes interessantes.

Retorne JSON:
{
  "1": {
    "location_id": 1,
    "name": "Nome do Local",
    "description": "Descrição geral",
    "is_starting_location": true,
    "is_locked": false,
    "areas": [
      {
        "area_id": 1,
        "name": "Nome da Área",
        "description": "Descrição detalhada da área",
        "connected_areas": [2, 3],
        "initially_visible": true,
        "discovery_level_required": 0,
        "details": [
          {
            "detail_id": 1,
            "name": "Detalhe observável",
            "description": "Descrição do que se vê",
            "discovery_level_required": 0,
            "has_clue": false
          }
        ],
        "characters": [],
        "objects": []
      }
    ]
  }
}

A primeira localização deve ter "is_starting_location": true.
Responda APENAS com o JSON válido.`;

        const response = await this.aiProvider.generateText(prompt, systemPrompt, {
            temperature: 0.8,
            maxTokens: 4000
        });

        return this.parseJSON(response);
    }

    async generateObjectsAndClues(concept, characters, locations, difficulty) {
        const numObjects = difficulty === 'easy' ? 10 : difficulty === 'medium' ? 15 : 20;
        const numClues = difficulty === 'easy' ? 8 : difficulty === 'medium' ? 12 : 15;

        const culprit = characters.find(c => c.is_culprit);

        const systemPrompt = `Você é um designer de puzzles e evidências para jogos de mistério.
Sempre responda em português brasileiro, com JSON válido.`;

        const prompt = `Para a história "${concept.title}":
Culpado: ${culprit.name}
Método do crime: ${concept.crime.criminalMethod}

Crie ${numObjects} objetos investigáveis e ${numClues} pistas.

Objetos devem conectar-se às pistas e à solução.
Alguns devem ser coletáveis (evidências).

Retorne JSON:
{
  "objects": [
    {
      "object_id": 1,
      "name": "Nome do Objeto",
      "is_collectible": true,
      "initial_location_id": 1,
      "initial_area_id": 1,
      "levels": [
        {
          "level_number": 0,
          "level_description": "O que se vê ao examinar",
          "evolution_trigger": "Como evoluir o conhecimento sobre este objeto"
        }
      ]
    }
  ],
  "clues": [
    {
      "clue_id": 1,
      "name": "Nome da Pista",
      "description": "Descrição da pista",
      "type": "evidência física",
      "relevance": 5,
      "is_key_evidence": true,
      "related_aspect": "culpado",
      "discovery_conditions": {
        "location_id": 1,
        "area_id": 1,
        "detail_id": 1
      }
    }
  ]
}

Pelo menos 5 pistas devem ter "is_key_evidence": true.
Responda APENAS com o JSON válido.`;

        const response = await this.aiProvider.generateText(prompt, systemPrompt, {
            temperature: 0.7,
            maxTokens: 4000
        });

        return this.parseJSON(response);
    }

    async generateSolution(concept, characters, objects, clues) {
        const culprit = characters.find(c => c.is_culprit);

        const systemPrompt = `Você é um especialista em criar soluções de mistérios.
Sempre responda em português brasileiro, com JSON válido.`;

        const prompt = `Para o mistério "${concept.title}":
Culpado: ${culprit.name}
Método: ${concept.crime.criminalMethod}

Crie critérios de solução e conclusão.

Retorne JSON:
{
  "solution_criteria": {
    "culprit_id": ${culprit.character_id},
    "motive_keywords": ["palavra-chave1", "palavra-chave2", "palavra-chave3"],
    "method_keywords": ["palavra-chave1", "palavra-chave2"]
  },
  "conclusion": "Texto de conclusão quando o jogador resolver o mistério (3-4 parágrafos)"
}

As palavras-chave devem ser termos importantes que o jogador precisa mencionar.
Responda APENAS com o JSON válido.`;

        const response = await this.aiProvider.generateText(prompt, systemPrompt, {
            temperature: 0.6,
            maxTokens: 1500
        });

        return this.parseJSON(response);
    }

    assembleStory(parts) {
        const {concept, characters, locations, objects, clues, solution} = parts;

        // Converter para formato esperado pelo jogo
        const personagensMap = {};
        characters.forEach(char => {
            personagensMap[char.character_id] = char;
        });

        return {
            historia_base: {
                title: concept.title,
                description: concept.description,
                introduction: concept.introduction,
                conclusion: solution.conclusion,
                solution_criteria: solution.solution_criteria,
                theme: concept.setting
            },
            ambientes: locations,
            personagens: personagensMap,
            objetos: objects,
            pistas: clues,
            sistema_especializacao: this.getDefaultSkillSystem()
        };
    }

    getDefaultSkillSystem() {
        return {
            "categorias": [
                {
                    "nome_interno": "analise_evidencias",
                    "nome_exibicao": "Análise de Evidências",
                    "descricao": "Habilidade de examinar e interpretar evidências físicas",
                    "niveis": {"1": 15, "2": 40, "3": 80}
                },
                {
                    "nome_interno": "conhecimento_historico",
                    "nome_exibicao": "Conhecimento Histórico",
                    "descricao": "Compreensão do contexto e história do local",
                    "niveis": {"1": 15, "2": 40, "3": 80}
                },
                {
                    "nome_interno": "interpretacao_comportamento",
                    "nome_exibicao": "Interpretação de Comportamento",
                    "descricao": "Capacidade de ler pessoas e suas intenções",
                    "niveis": {"1": 15, "2": 40, "3": 80}
                },
                {
                    "nome_interno": "descoberta_ambiental",
                    "nome_exibicao": "Descoberta Ambiental",
                    "descricao": "Percepção aguçada para detalhes do ambiente",
                    "niveis": {"1": 15, "2": 40, "3": 80}
                },
                {
                    "nome_interno": "conexao_informacoes",
                    "nome_exibicao": "Conexão de Informações",
                    "descricao": "Habilidade de relacionar pistas e formar teorias",
                    "niveis": {"1": 15, "2": 40, "3": 80}
                }
            ]
        };
    }

    parseJSON(text) {
        try {
            // Tentar extrair JSON do texto (caso tenha texto extra)
            const jsonMatch = text.match(/\{[\s\S]*\}|\[[\s\S]*\]/);
            if (jsonMatch) {
                return JSON.parse(jsonMatch[0]);
            }
            return JSON.parse(text);
        } catch (error) {
            console.error('Error parsing JSON:', error);
            console.log('Raw text:', text);
            throw new Error('Failed to parse AI response as JSON');
        }
    }
}

// Make available globally
window.StoryGenerator = StoryGenerator;
