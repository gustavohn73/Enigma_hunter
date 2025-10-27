// Game Engine for Enigma Hunter
class GameEngine {
    constructor() {
        this.gameData = {
            historia_base: null,
            ambientes: {},
            personagens: {},
            objetos: [],
            pistas: [],
            sistema_especializacao: null
        };

        this.playerState = {
            playerId: null,
            currentLocation: null,
            currentArea: null,
            inventory: [],
            discoveredClues: [],
            characterLevels: {},
            locationLevels: {},
            objectLevels: {},
            lastSeenDetails: {},
            skills: {
                analise_evidencias: 0,
                conhecimento_historico: 0,
                interpretacao_comportamento: 0,
                descoberta_ambiental: 0,
                conexao_informacoes: 0
            },
            examinedObjects: [],
            caseSolved: false,
            finalScore: null,
            solvedAt: null
        };

        this.dynamicDetailsCache = {
            descriptions: {},
            details: {}
        };

        this.conversationHistory = [];
        this.db = window.firebaseServices.db;
        this.functions = window.firebaseServices.functions;
    }

    async loadGameData() {
        try {
            console.log('Loading game data from Firestore...');

            // Load historia_base
            const historiaDoc = await this.db.collection('game_data').doc('historia_base').get();
            if (historiaDoc.exists) {
                this.gameData.historia_base = historiaDoc.data();
            }

            // Load ambientes
            const ambientesSnapshot = await this.db.collection('game_data').doc('ambientes').get();
            if (ambientesSnapshot.exists) {
                this.gameData.ambientes = ambientesSnapshot.data();
            }

            // Load personagens
            const personagensSnapshot = await this.db.collection('game_data').doc('personagens').get();
            if (personagensSnapshot.exists) {
                this.gameData.personagens = personagensSnapshot.data();
            }

            // Load objetos
            const objetosSnapshot = await this.db.collection('game_data').doc('objetos').get();
            if (objetosSnapshot.exists) {
                this.gameData.objetos = objetosSnapshot.data().items || [];
            }

            // Load pistas
            const pistasSnapshot = await this.db.collection('game_data').doc('pistas').get();
            if (pistasSnapshot.exists) {
                this.gameData.pistas = pistasSnapshot.data().items || [];
            }

            // Load sistema_especializacao
            const sistemaSnapshot = await this.db.collection('game_data').doc('sistema_especializacao').get();
            if (sistemaSnapshot.exists) {
                this.gameData.sistema_especializacao = sistemaSnapshot.data();
            }

            // Set initial location
            for (const [locId, location] of Object.entries(this.gameData.ambientes)) {
                if (location.is_starting_location) {
                    this.playerState.currentLocation = parseInt(locId);
                    if (location.areas && location.areas.length > 0) {
                        this.playerState.currentArea = location.areas[0].area_id;
                    }
                    break;
                }
            }

            console.log('Game data loaded successfully');
            return true;
        } catch (error) {
            console.error('Error loading game data:', error);
            throw error;
        }
    }

    async saveGame() {
        try {
            const playerId = this.playerState.playerId;
            if (!playerId) {
                console.error('No player ID set');
                return false;
            }

            const saveData = {
                currentLocation: this.playerState.currentLocation,
                currentArea: this.playerState.currentArea,
                playerData: {
                    inventory: this.playerState.inventory,
                    discoveredClues: this.playerState.discoveredClues,
                    characterLevels: this.playerState.characterLevels,
                    locationLevels: this.playerState.locationLevels,
                    objectLevels: this.playerState.objectLevels,
                    lastSeenDetails: this.playerState.lastSeenDetails,
                    skills: this.playerState.skills,
                    examinedObjects: this.playerState.examinedObjects,
                    caseSolved: this.playerState.caseSolved,
                    finalScore: this.playerState.finalScore,
                    solvedAt: this.playerState.solvedAt
                },
                dynamicDetailsCache: this.dynamicDetailsCache,
                lastSaved: new Date().toISOString()
            };

            await this.db.collection('guest_saves').doc(playerId).set(saveData);
            console.log('Game saved successfully');
            return true;
        } catch (error) {
            console.error('Error saving game:', error);
            return false;
        }
    }

    async loadGame(playerId) {
        try {
            this.playerState.playerId = playerId;
            const saveDoc = await this.db.collection('guest_saves').doc(playerId).get();

            if (!saveDoc.exists) {
                console.log('No save found for player:', playerId);
                return false;
            }

            const saveData = saveDoc.data();
            this.playerState.currentLocation = saveData.currentLocation;
            this.playerState.currentArea = saveData.currentArea;

            if (saveData.playerData) {
                Object.assign(this.playerState, saveData.playerData);
            }

            if (saveData.dynamicDetailsCache) {
                this.dynamicDetailsCache = saveData.dynamicDetailsCache;
            }

            console.log('Game loaded successfully');
            return true;
        } catch (error) {
            console.error('Error loading game:', error);
            return false;
        }
    }

    async listSavedGames() {
        try {
            const savesSnapshot = await this.db.collection('guest_saves').get();
            const saves = [];

            savesSnapshot.forEach(doc => {
                const data = doc.data();
                const locationName = this.getLocationName(data.currentLocation);

                saves.push({
                    playerId: doc.id,
                    lastSaved: data.lastSaved,
                    location: locationName,
                    cluesCount: data.playerData?.discoveredClues?.length || 0,
                    caseSolved: data.playerData?.caseSolved || false,
                    finalScore: data.playerData?.finalScore || null
                });
            });

            saves.sort((a, b) => new Date(b.lastSaved) - new Date(a.lastSaved));
            return saves;
        } catch (error) {
            console.error('Error listing saved games:', error);
            return [];
        }
    }

    getLocationName(locationId) {
        const location = this.gameData.ambientes[locationId];
        return location ? location.name : 'Desconhecido';
    }

    getCurrentLocation() {
        return this.gameData.ambientes[this.playerState.currentLocation];
    }

    getCurrentArea() {
        const location = this.getCurrentLocation();
        if (!location || !location.areas) return null;
        return location.areas.find(a => a.area_id === this.playerState.currentArea);
    }

    getLocationDiscoveryLevel(areaId) {
        return this.playerState.locationLevels[areaId] || 0;
    }

    increaseLocationDiscovery(areaId) {
        const currentLevel = this.getLocationDiscoveryLevel(areaId);
        this.playerState.locationLevels[areaId] = Math.min(currentLevel + 1, 3);
    }

    getObjectDiscoveryLevel(objectId) {
        return this.playerState.objectLevels[objectId] || 0;
    }

    increaseObjectDiscoveryLevel(objectId) {
        const currentLevel = this.getObjectDiscoveryLevel(objectId);
        const obj = this.getObjectById(objectId);
        if (obj && currentLevel < obj.levels.length - 1) {
            this.playerState.objectLevels[objectId] = currentLevel + 1;
            return true;
        }
        return false;
    }

    getCharacterLevel(characterId) {
        return this.playerState.characterLevels[characterId] || 0;
    }

    getObjectById(objectId) {
        return this.gameData.objetos.find(obj => obj.object_id === objectId);
    }

    getClueById(clueId) {
        return this.gameData.pistas.find(clue => clue.clue_id === clueId);
    }

    getCharacterById(characterId) {
        return this.gameData.personagens[characterId];
    }

    getObjectsInArea(locationId, areaId) {
        return this.gameData.objetos.filter(obj => {
            if (obj.initial_location_id === locationId && obj.initial_area_id === areaId) {
                // Se for coletável e já está no inventário, não mostrar
                if (obj.is_collectible && this.playerState.inventory.includes(obj.object_id)) {
                    return false;
                }
                return true;
            }
            return false;
        });
    }

    getCharactersInArea(locationId, areaId) {
        const characters = [];
        for (const [charId, char] of Object.entries(this.gameData.personagens)) {
            if (char.area_id === areaId) {
                characters.push({ ...char, character_id: parseInt(charId) });
            }
        }
        return characters;
    }

    discoverClueByDetail(locationId, areaId, detailId) {
        for (const clue of this.gameData.pistas) {
            const conditions = clue.discovery_conditions;

            if (Array.isArray(conditions)) {
                for (const condition of conditions) {
                    if (condition.location_id === locationId &&
                        condition.area_id === areaId &&
                        condition.detail_id === detailId) {
                        if (!this.playerState.discoveredClues.includes(clue.clue_id)) {
                            this.playerState.discoveredClues.push(clue.clue_id);
                            return clue;
                        }
                    }
                }
            } else if (typeof conditions === 'object') {
                if (conditions.location_id === locationId &&
                    conditions.area_id === areaId &&
                    conditions.detail_id === detailId) {
                    if (!this.playerState.discoveredClues.includes(clue.clue_id)) {
                        this.playerState.discoveredClues.push(clue.clue_id);
                        return clue;
                    }
                }
            }
        }
        return null;
    }

    discoverCluesByCharacter(characterId) {
        const discoveredClues = [];
        for (const clue of this.gameData.pistas) {
            const conditions = clue.discovery_conditions;
            if (conditions && conditions.character_id === characterId) {
                if (!this.playerState.discoveredClues.includes(clue.clue_id)) {
                    this.playerState.discoveredClues.push(clue.clue_id);
                    discoveredClues.push(clue);
                }
            }
        }
        return discoveredClues;
    }

    increaseSkillByObject(objectId) {
        const skillMapping = {
            1: "conhecimento_historico",
            2: "conexao_informacoes",
            3: "analise_evidencias",
            4: "conhecimento_historico",
            5: "conexao_informacoes",
            6: "conhecimento_historico",
            7: "conhecimento_historico",
            8: "descoberta_ambiental",
            9: "interpretacao_comportamento",
            10: "analise_evidencias",
            11: "analise_evidencias",
            12: "conhecimento_historico",
            13: "conexao_informacoes",
            14: "conexao_informacoes",
            15: "analise_evidencias",
            16: "conexao_informacoes",
            17: "conhecimento_historico",
            18: "analise_evidencias",
            19: "conexao_informacoes",
            20: "analise_evidencias"
        };

        if (skillMapping[objectId]) {
            const skill = skillMapping[objectId];
            this.playerState.skills[skill] = Math.min(this.playerState.skills[skill] + 10, 100);

            if (!this.playerState.examinedObjects.includes(objectId.toString())) {
                this.playerState.examinedObjects.push(objectId.toString());
                return skill;
            }
        }
        return null;
    }

    checkDialogueRequirements(trigger) {
        if (!trigger.requirements) return true;

        for (const req of trigger.requirements) {
            const reqType = req.requirement_type;

            if (reqType === "evidence" && req.required_object_id) {
                const requiredObjects = Array.isArray(req.required_object_id) ?
                    req.required_object_id : [req.required_object_id];

                if (!requiredObjects.some(objId => this.playerState.inventory.includes(objId))) {
                    return false;
                }
            } else if (reqType === "knowledge" && req.required_object_id) {
                const requiredObjects = Array.isArray(req.required_object_id) ?
                    req.required_object_id : [req.required_object_id];

                if (!requiredObjects.some(objId => this.getObjectDiscoveryLevel(objId) > 0)) {
                    return false;
                }
            } else if (reqType === "observation" && req.required_detail_id) {
                const detailIds = Array.isArray(req.required_detail_id) ?
                    req.required_detail_id : [req.required_detail_id];

                let found = false;
                for (const detailId of detailIds) {
                    for (const areaKey in this.playerState.lastSeenDetails) {
                        if (this.playerState.lastSeenDetails[areaKey].includes(detailId)) {
                            found = true;
                            break;
                        }
                    }
                    if (found) break;
                }

                if (!found) return false;
            }
        }

        return true;
    }

    async enhanceTextWithAI(context, text, instruction) {
        try {
            const enhanceText = this.functions.httpsCallable('enhanceText');
            const result = await enhanceText({ context, text, instruction });
            return result.data.enhancedText || text;
        } catch (error) {
            console.error('Error enhancing text:', error);
            return text;
        }
    }

    async generateNPCDialogue(character, playerQuestion) {
        try {
            const generateDialogue = this.functions.httpsCallable('generateNPCDialogue');
            const result = await generateDialogue({
                character: character,
                characterLevel: this.getCharacterLevel(character.character_id),
                question: playerQuestion
            });
            return result.data.response;
        } catch (error) {
            console.error('Error generating NPC dialogue:', error);
            return "Não consigo responder a isso no momento.";
        }
    }

    async checkForTrigger(character, playerQuestion) {
        const charId = character.character_id;
        const charLevel = this.getCharacterLevel(charId);
        const questionLower = playerQuestion.toLowerCase();

        for (const level of character.levels || []) {
            if (level.level_number <= charLevel && level.triggers) {
                for (const trigger of level.triggers) {
                    const keyword = (trigger.trigger_keyword || "").toLowerCase();

                    if (keyword && questionLower.includes(keyword)) {
                        if (level.is_defensive) {
                            const hasRequirements = this.checkDialogueRequirements(trigger);

                            if (hasRequirements) {
                                // Success
                                const successResponse = trigger.success_response ||
                                    "Você descobriu algo importante!";

                                // Aumentar nível do personagem
                                if (charLevel < character.levels.length - 1) {
                                    this.playerState.characterLevels[charId] = charLevel + 1;

                                    // Descobrir pistas relacionadas
                                    const newClues = this.discoverCluesByCharacter(charId);

                                    // Salvar automaticamente
                                    await this.saveGame();
                                }

                                return {
                                    response: successResponse,
                                    levelUp: true,
                                    newClues: this.discoverCluesByCharacter(charId)
                                };
                            } else {
                                // Fail
                                return {
                                    response: trigger.fail_response || "Não tenho nada a dizer sobre isso.",
                                    levelUp: false
                                };
                            }
                        } else {
                            // Não defensivo
                            return {
                                response: trigger.success_response || "Interessante pergunta...",
                                levelUp: false
                            };
                        }
                    }
                }
            }
        }

        return null;
    }

    collectObject(objectId) {
        if (!this.playerState.inventory.includes(objectId)) {
            this.playerState.inventory.push(objectId);
            return true;
        }
        return false;
    }

    markDetailAsSeen(areaId, detailId) {
        const areaKey = areaId.toString();
        if (!this.playerState.lastSeenDetails[areaKey]) {
            this.playerState.lastSeenDetails[areaKey] = [];
        }
        if (!this.playerState.lastSeenDetails[areaKey].includes(detailId)) {
            this.playerState.lastSeenDetails[areaKey].push(detailId);
        }
    }

    getKeyEvidenceCount() {
        return this.playerState.discoveredClues.filter(clueId => {
            const clue = this.getClueById(clueId);
            return clue && clue.is_key_evidence;
        }).length;
    }

    processAccusation(suspectId, motive, method) {
        const criteria = this.gameData.historia_base.solution_criteria;

        const culpritCorrect = parseInt(suspectId) === criteria.culprit_id;

        const motiveLower = motive.toLowerCase();
        const motiveCorrect = criteria.motive_keywords.some(keyword =>
            motiveLower.includes(keyword.toLowerCase())
        );

        const methodLower = method.toLowerCase();
        const methodCorrect = criteria.method_keywords.some(keyword =>
            methodLower.includes(keyword.toLowerCase())
        );

        let score = 0;
        if (culpritCorrect) score += 50;
        if (motiveCorrect) score += 25;
        if (methodCorrect) score += 25;

        const success = score >= 75;

        if (success) {
            this.playerState.caseSolved = true;
            this.playerState.finalScore = score;
            this.playerState.solvedAt = new Date().toISOString();
        }

        return {
            success,
            score,
            culpritCorrect,
            motiveCorrect,
            methodCorrect
        };
    }

    getSkillInfo() {
        const skillNames = {
            "analise_evidencias": "Análise de Evidências",
            "conhecimento_historico": "Conhecimento Histórico",
            "interpretacao_comportamento": "Interpretação de Comportamento",
            "descoberta_ambiental": "Descoberta Ambiental",
            "conexao_informacoes": "Conexão de Informações"
        };

        const skills = [];
        const categories = this.gameData.sistema_especializacao?.categorias || [];

        for (const [skillId, level] of Object.entries(this.playerState.skills)) {
            const category = categories.find(c => c.nome_interno === skillId);

            let skillLevel = 0;
            if (category && category.niveis) {
                for (const [lvl, threshold] of Object.entries(category.niveis)) {
                    if (level >= threshold) {
                        skillLevel = parseInt(lvl);
                    }
                }
            }

            skills.push({
                id: skillId,
                name: skillNames[skillId] || skillId,
                description: category?.descricao || "",
                level: skillLevel,
                points: level,
                maxPoints: 100
            });
        }

        return skills;
    }
}

// Make GameEngine available globally
window.GameEngine = GameEngine;
