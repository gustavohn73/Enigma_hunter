// UI Controller for Enigma Hunter
class UIController {
    constructor() {
        this.gameEngine = new GameEngine();
        this.currentCharacter = null;
        this.init();
    }

    async init() {
        // Show loading screen
        this.showScreen('loading-screen');

        try {
            // Load game data
            await this.gameEngine.loadGameData();

            // Hide loading screen and show main menu
            this.showScreen('main-menu');

            // Setup event listeners
            this.setupEventListeners();

            // Initialize AI UI Controller
            this.aiController = new AIUIController(this);

        } catch (error) {
            console.error('Failed to initialize game:', error);
            alert('Erro ao carregar o jogo. Por favor, recarregue a página.');
        }
    }

    setupEventListeners() {
        // Main Menu
        document.getElementById('btn-new-game').addEventListener('click', () => this.showNewGameScreen());
        document.getElementById('btn-load-game').addEventListener('click', () => this.showLoadGameScreen());
        document.getElementById('btn-instructions').addEventListener('click', () => this.showInstructions());

        // New Game Screen
        document.getElementById('btn-start-game').addEventListener('click', () => this.startNewGame());
        document.getElementById('btn-cancel-new-game').addEventListener('click', () => this.showScreen('main-menu'));

        // Load Game Screen
        document.getElementById('btn-cancel-load').addEventListener('click', () => this.showScreen('main-menu'));

        // Instructions Screen
        document.getElementById('btn-close-instructions').addEventListener('click', () => this.showScreen('main-menu'));

        // Game Screen - Side Panel
        document.getElementById('btn-inventory').addEventListener('click', () => this.showInventory());
        document.getElementById('btn-clues').addEventListener('click', () => this.showClues());
        document.getElementById('btn-skills').addEventListener('click', () => this.showSkills());
        document.getElementById('btn-save').addEventListener('click', () => this.saveGame());
        document.getElementById('btn-accuse').addEventListener('click', () => this.showAccusationModal());
        document.getElementById('btn-menu').addEventListener('click', () => this.showGameMenu());

        // Modals
        document.getElementById('btn-close-inventory').addEventListener('click', () => this.hideModal('inventory-modal'));
        document.getElementById('btn-close-clues').addEventListener('click', () => this.hideModal('clues-modal'));
        document.getElementById('btn-close-skills').addEventListener('click', () => this.hideModal('skills-modal'));
        document.getElementById('btn-cancel-accusation').addEventListener('click', () => this.hideModal('accusation-modal'));
        document.getElementById('btn-submit-accusation').addEventListener('click', () => this.submitAccusation());
        document.getElementById('btn-close-result').addEventListener('click', () => this.hideModal('result-modal'));

        // Conversation
        document.getElementById('btn-send-message').addEventListener('click', () => this.sendMessage());
        document.getElementById('btn-end-conversation').addEventListener('click', () => this.endConversation());
        document.getElementById('conversation-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
    }

    showScreen(screenId) {
        const screens = ['loading-screen', 'main-menu', 'player-id-screen', 'load-game-screen',
                        'instructions-screen', 'game-screen'];
        screens.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.classList.toggle('hidden', id !== screenId);
            }
        });
    }

    showModal(modalId) {
        document.getElementById(modalId).classList.remove('hidden');
    }

    hideModal(modalId) {
        document.getElementById(modalId).classList.add('hidden');
    }

    showNewGameScreen() {
        this.showScreen('player-id-screen');
        document.getElementById('player-id-input').value = '';
        document.getElementById('player-id-input').focus();
    }

    async showLoadGameScreen() {
        this.showScreen('load-game-screen');
        const saves = await this.gameEngine.listSavedGames();
        const listElement = document.getElementById('saved-games-list');

        if (saves.length === 0) {
            listElement.innerHTML = '<p class="no-saves">Nenhum jogo salvo encontrado.</p>';
            return;
        }

        listElement.innerHTML = '';
        saves.forEach(save => {
            const saveItem = document.createElement('div');
            saveItem.className = 'saved-game-item';
            saveItem.innerHTML = `
                <h4>Jogador: ${save.playerId}</h4>
                <p>Local: ${save.location}</p>
                <p>Pistas descobertas: ${save.cluesCount}</p>
                <p>Status: ${save.caseSolved ? '✓ Caso Resolvido ('+save.finalScore+' pontos)' : '📜 Em andamento'}</p>
                <p>Último save: ${new Date(save.lastSaved).toLocaleString('pt-BR')}</p>
            `;
            saveItem.addEventListener('click', () => this.loadGame(save.playerId));
            listElement.appendChild(saveItem);
        });
    }

    showInstructions() {
        this.showScreen('instructions-screen');
    }

    async startNewGame() {
        let playerId = document.getElementById('player-id-input').value.trim();

        if (!playerId) {
            playerId = window.firebaseServices.generateSessionId();
        }

        // Check if save exists
        const saveExists = await this.checkSaveExists(playerId);
        if (saveExists) {
            const overwrite = confirm(`Já existe um jogo salvo com o ID "${playerId}". Deseja sobrescrevê-lo?`);
            if (!overwrite) return;
        }

        this.gameEngine.playerState.playerId = playerId;
        await this.gameEngine.saveGame();

        this.showGameScreen();
    }

    async checkSaveExists(playerId) {
        try {
            const saveDoc = await this.gameEngine.db.collection('guest_saves').doc(playerId).get();
            return saveDoc.exists;
        } catch (error) {
            console.error('Error checking save:', error);
            return false;
        }
    }

    async loadGame(playerId) {
        const success = await this.gameEngine.loadGame(playerId);
        if (success) {
            this.showGameScreen();
        } else {
            alert('Erro ao carregar o jogo.');
        }
    }

    showGameScreen() {
        this.showScreen('game-screen');
        this.updateGameDisplay();
    }

    updateGameDisplay() {
        const location = this.gameEngine.getCurrentLocation();
        const area = this.gameEngine.getCurrentArea();

        if (!location || !area) {
            console.error('Invalid location or area');
            return;
        }

        // Update header
        document.getElementById('current-location-name').textContent = location.name;
        document.getElementById('current-area-name').textContent = area.name;

        // Update narrative text
        const narrativeElement = document.getElementById('narrative-text');
        narrativeElement.textContent = area.description;

        // Update badges
        document.getElementById('inventory-count').textContent = this.gameEngine.playerState.inventory.length;
        document.getElementById('clues-count').textContent = this.gameEngine.playerState.discoveredClues.length;

        // Build options
        this.buildOptions();
    }

    buildOptions() {
        const container = document.getElementById('options-container');
        container.innerHTML = '';

        const area = this.gameEngine.getCurrentArea();
        const location = this.gameEngine.getCurrentLocation();

        // Details to explore
        const visibleDetails = (area.details || []).filter(d =>
            d.discovery_level_required <= this.gameEngine.getLocationDiscoveryLevel(this.gameEngine.playerState.currentArea)
        );

        if (visibleDetails.length > 0 || this.hasObjectsOrCharacters()) {
            const exploreSection = document.createElement('div');
            exploreSection.className = 'option-section';
            exploreSection.innerHTML = '<h3>Você nota:</h3>';

            // Add details
            visibleDetails.forEach(detail => {
                const btn = this.createOptionButton(`Explorar ${detail.name}`, () => this.exploreDetail(detail));
                exploreSection.appendChild(btn);
                this.gameEngine.markDetailAsSeen(this.gameEngine.playerState.currentArea, detail.detail_id);
            });

            // Add objects
            const objects = this.gameEngine.getObjectsInArea(
                this.gameEngine.playerState.currentLocation,
                this.gameEngine.playerState.currentArea
            );
            objects.forEach(obj => {
                const btn = this.createOptionButton(`Examinar ${obj.name}`, () => this.examineObject(obj));
                exploreSection.appendChild(btn);
            });

            container.appendChild(exploreSection);
        }

        // Connected areas
        const connectedAreas = (area.connected_areas || [])
            .map(areaId => location.areas.find(a => a.area_id === areaId))
            .filter(a => a && a.initially_visible !== false);

        if (connectedAreas.length > 0) {
            const areasSection = document.createElement('div');
            areasSection.className = 'option-section';
            areasSection.innerHTML = '<h3>Áreas conectadas:</h3>';

            connectedAreas.forEach(targetArea => {
                const btn = this.createOptionButton(`Ir para ${targetArea.name}`, () => this.moveToArea(targetArea));
                areasSection.appendChild(btn);
            });

            container.appendChild(areasSection);
        }

        // Characters
        const characters = this.gameEngine.getCharactersInArea(
            this.gameEngine.playerState.currentLocation,
            this.gameEngine.playerState.currentArea
        );

        if (characters.length > 0) {
            const charsSection = document.createElement('div');
            charsSection.className = 'option-section';
            charsSection.innerHTML = '<h3>Personagens presentes:</h3>';

            characters.forEach(char => {
                const btn = this.createOptionButton(`Falar com ${char.name}`, () => this.startConversation(char));
                charsSection.appendChild(btn);
            });

            container.appendChild(charsSection);
        }
    }

    hasObjectsOrCharacters() {
        const objects = this.gameEngine.getObjectsInArea(
            this.gameEngine.playerState.currentLocation,
            this.gameEngine.playerState.currentArea
        );
        const characters = this.gameEngine.getCharactersInArea(
            this.gameEngine.playerState.currentLocation,
            this.gameEngine.playerState.currentArea
        );
        return objects.length > 0 || characters.length > 0;
    }

    createOptionButton(text, onClick) {
        const btn = document.createElement('button');
        btn.className = 'option-btn';
        btn.textContent = text;
        btn.addEventListener('click', onClick);
        return btn;
    }

    exploreDetail(detail) {
        const narrativeElement = document.getElementById('narrative-text');
        narrativeElement.innerHTML = `<h3 style="color: var(--secondary-color); margin-bottom: 15px;">Explorando: ${detail.name}</h3><p>${detail.description}</p>`;

        // Check for clues
        const clue = this.gameEngine.discoverClueByDetail(
            this.gameEngine.playerState.currentLocation,
            this.gameEngine.playerState.currentArea,
            detail.detail_id
        );

        if (clue) {
            this.showNotification(`Você descobriu uma nova pista: ${clue.name}!`, 'success');
            this.gameEngine.saveGame();
        }

        // Increase location discovery
        this.gameEngine.increaseLocationDiscovery(this.gameEngine.playerState.currentArea);

        // Scroll to top
        document.querySelector('.main-panel').scrollTop = 0;
    }

    examineObject(obj) {
        const level = this.gameEngine.getObjectDiscoveryLevel(obj.object_id);
        const levelInfo = obj.levels[level];

        const narrativeElement = document.getElementById('narrative-text');
        narrativeElement.innerHTML = `<h3 style="color: var(--secondary-color); margin-bottom: 15px;">Examinando: ${obj.name}</h3><p>${levelInfo.level_description}</p>`;

        // Check if collectible
        if (obj.is_collectible && !this.gameEngine.playerState.inventory.includes(obj.object_id)) {
            const takeBtn = document.createElement('button');
            takeBtn.className = 'primary-btn';
            takeBtn.textContent = 'Pegar este objeto';
            takeBtn.style.marginTop = '15px';
            takeBtn.addEventListener('click', () => {
                this.gameEngine.collectObject(obj.object_id);
                this.showNotification(`Você pegou: ${obj.name}`, 'success');
                this.gameEngine.saveGame();
                this.updateGameDisplay();
            });
            narrativeElement.appendChild(takeBtn);
        }

        // Increase skills
        const skill = this.gameEngine.increaseSkillByObject(obj.object_id);
        if (skill) {
            const skillNames = {
                "analise_evidencias": "Análise de Evidências",
                "conhecimento_historico": "Conhecimento Histórico",
                "interpretacao_comportamento": "Interpretação de Comportamento",
                "descoberta_ambiental": "Descoberta Ambiental",
                "conexao_informacoes": "Conexão de Informações"
            };
            this.showNotification(`Sua habilidade de ${skillNames[skill]} aumentou!`, 'info');
        }

        // Update display
        this.updateGameDisplay();

        // Scroll to top
        document.querySelector('.main-panel').scrollTop = 0;
    }

    moveToArea(targetArea) {
        this.gameEngine.playerState.currentArea = targetArea.area_id;
        this.updateGameDisplay();
        this.showNotification(`Você se moveu para ${targetArea.name}`, 'info');
    }

    startConversation(character) {
        this.currentCharacter = character;
        this.gameEngine.conversationHistory = [];

        const narrativeElement = document.getElementById('narrative-text');
        narrativeElement.innerHTML = `
            <h3 style="color: var(--secondary-color); margin-bottom: 15px;">Conversando com ${character.name}</h3>
            <p>${character.base_description}</p>
        `;

        document.getElementById('options-container').classList.add('hidden');
        document.getElementById('conversation-panel').classList.remove('hidden');
        document.getElementById('conversation-history').innerHTML = '';
        document.getElementById('conversation-input').value = '';
        document.getElementById('conversation-input').focus();

        // Add initial greeting
        this.addConversationMessage(character.name, 'Olá, em que posso ajudar?', 'npc');
    }

    addConversationMessage(speaker, message, type) {
        const historyElement = document.getElementById('conversation-history');
        const messageDiv = document.createElement('div');
        messageDiv.className = `conversation-message ${type}`;
        messageDiv.innerHTML = `<div class="message-speaker">${speaker}:</div><div>${message}</div>`;
        historyElement.appendChild(messageDiv);
        historyElement.scrollTop = historyElement.scrollHeight;
    }

    async sendMessage() {
        const input = document.getElementById('conversation-input');
        const question = input.value.trim();

        if (!question) return;

        input.value = '';
        this.addConversationMessage('Você', question, 'player');

        // Check for trigger first
        const triggerResult = await this.gameEngine.checkForTrigger(this.currentCharacter, question);

        if (triggerResult) {
            this.addConversationMessage(this.currentCharacter.name, triggerResult.response, 'npc');

            if (triggerResult.levelUp) {
                this.showNotification('Relacionamento com personagem aumentou!', 'success');
            }

            if (triggerResult.newClues && triggerResult.newClues.length > 0) {
                triggerResult.newClues.forEach(clue => {
                    this.showNotification(`Nova pista descoberta: ${clue.name}!`, 'success');
                });
            }

            this.updateGameDisplay();
        } else {
            // Generate dialogue with AI
            try {
                const response = await this.gameEngine.generateNPCDialogue(this.currentCharacter, question);
                this.addConversationMessage(this.currentCharacter.name, response, 'npc');
            } catch (error) {
                this.addConversationMessage(this.currentCharacter.name, 'Desculpe, não consigo responder no momento.', 'npc');
            }
        }

        // Increase skill
        this.gameEngine.playerState.skills.interpretacao_comportamento = Math.min(
            this.gameEngine.playerState.skills.interpretacao_comportamento + 5,
            100
        );

        input.focus();
    }

    endConversation() {
        this.currentCharacter = null;
        this.gameEngine.conversationHistory = [];
        document.getElementById('options-container').classList.remove('hidden');
        document.getElementById('conversation-panel').classList.add('hidden');
        this.updateGameDisplay();
    }

    showInventory() {
        const listElement = document.getElementById('inventory-list');
        listElement.innerHTML = '';

        if (this.gameEngine.playerState.inventory.length === 0) {
            listElement.innerHTML = '<p class="no-saves">Seu inventário está vazio.</p>';
        } else {
            this.gameEngine.playerState.inventory.forEach(objId => {
                const obj = this.gameEngine.getObjectById(objId);
                if (obj) {
                    const card = this.createItemCard(obj.name, obj.levels[0].level_description, 'Objeto');
                    listElement.appendChild(card);
                }
            });
        }

        this.showModal('inventory-modal');
    }

    showClues() {
        const listElement = document.getElementById('clues-list');
        listElement.innerHTML = '';

        if (this.gameEngine.playerState.discoveredClues.length === 0) {
            listElement.innerHTML = '<p class="no-saves">Você ainda não descobriu nenhuma pista.</p>';
        } else {
            const clues = this.gameEngine.playerState.discoveredClues
                .map(id => this.gameEngine.getClueById(id))
                .filter(c => c)
                .sort((a, b) => (b.relevance || 0) - (a.relevance || 0));

            clues.forEach(clue => {
                const stars = '★'.repeat(clue.relevance || 0);
                const card = this.createItemCard(
                    clue.name,
                    clue.description,
                    clue.type,
                    stars
                );
                listElement.appendChild(card);
            });
        }

        this.showModal('clues-modal');
    }

    showSkills() {
        const listElement = document.getElementById('skills-list');
        listElement.innerHTML = '';

        const skills = this.gameEngine.getSkillInfo();

        skills.forEach(skill => {
            const skillDiv = document.createElement('div');
            skillDiv.className = 'skill-item';

            const progress = (skill.points / skill.maxPoints) * 100;

            skillDiv.innerHTML = `
                <h4>${skill.name} (Nível ${skill.level})</h4>
                <p>${skill.description}</p>
                <div class="skill-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    <span class="progress-text">${skill.points}/${skill.maxPoints}</span>
                </div>
            `;

            listElement.appendChild(skillDiv);
        });

        this.showModal('skills-modal');
    }

    createItemCard(title, description, type, extra = '') {
        const card = document.createElement('div');
        card.className = 'item-card';
        card.innerHTML = `
            <h4>${title}</h4>
            <p>${description}</p>
            <span class="item-type">${type}</span>
            ${extra ? `<div class="relevance-stars">${extra}</div>` : ''}
        `;
        return card;
    }

    async saveGame() {
        const success = await this.gameEngine.saveGame();
        if (success) {
            this.showNotification('Jogo salvo com sucesso!', 'success');
        } else {
            this.showNotification('Erro ao salvar o jogo.', 'error');
        }
    }

    showGameMenu() {
        const confirmExit = confirm('Deseja voltar ao menu principal? (O jogo será salvo automaticamente)');
        if (confirmExit) {
            this.gameEngine.saveGame();
            this.showScreen('main-menu');
        }
    }

    showAccusationModal() {
        const keyEvidenceCount = this.gameEngine.getKeyEvidenceCount();
        const minEvidence = 5;

        const warningElement = document.getElementById('evidence-warning');
        const submitBtn = document.getElementById('btn-submit-accusation');

        if (keyEvidenceCount < minEvidence) {
            warningElement.classList.remove('hidden');
            submitBtn.disabled = true;
            submitBtn.style.opacity = '0.5';
            submitBtn.style.cursor = 'not-allowed';
        } else {
            warningElement.classList.add('hidden');
            submitBtn.disabled = false;
            submitBtn.style.opacity = '1';
            submitBtn.style.cursor = 'pointer';
        }

        // Populate suspects
        const selectElement = document.getElementById('suspect-select');
        selectElement.innerHTML = '<option value="">Selecione um suspeito...</option>';

        for (const [charId, char] of Object.entries(this.gameEngine.gameData.personagens)) {
            const option = document.createElement('option');
            option.value = charId;
            option.textContent = char.name;
            selectElement.appendChild(option);
        }

        // Clear inputs
        document.getElementById('motive-input').value = '';
        document.getElementById('method-input').value = '';

        this.showModal('accusation-modal');
    }

    async submitAccusation() {
        const suspectId = document.getElementById('suspect-select').value;
        const motive = document.getElementById('motive-input').value.trim();
        const method = document.getElementById('method-input').value.trim();

        if (!suspectId || !motive || !method) {
            alert('Por favor, preencha todos os campos.');
            return;
        }

        const result = this.gameEngine.processAccusation(suspectId, motive, method);

        this.hideModal('accusation-modal');

        // Save game
        await this.gameEngine.saveGame();

        // Show result
        this.showAccusationResult(result);
    }

    showAccusationResult(result) {
        const titleElement = document.getElementById('result-title');
        const contentElement = document.getElementById('result-content');

        if (result.success) {
            titleElement.textContent = 'Parabéns!';
            titleElement.style.color = 'var(--accent-green)';
            contentElement.innerHTML = `
                <h3 style="color: var(--accent-green);">Você resolveu o mistério!</h3>
                <p>Sua acusação está substancialmente correta!</p>
                <div class="score-display">${result.score}/100 pontos</div>
                <p>${this.gameEngine.gameData.historia_base.conclusion || 'O mistério foi resolvido com sucesso!'}</p>
            `;
        } else {
            titleElement.textContent = 'Acusação Incompleta';
            titleElement.style.color = 'var(--accent-red)';

            let feedback = '<p>Sua acusação não é conclusiva. Continue investigando.</p>';
            feedback += `<div class="score-display">${result.score}/100 pontos</div>`;

            if (!result.culpritCorrect) {
                feedback += '<p style="color: var(--secondary-color);">❌ As evidências não apontam para esta pessoa como culpado.</p>';
            } else {
                feedback += '<p style="color: var(--accent-green);">✓ Você identificou o culpado corretamente!</p>';
            }

            if (!result.motiveCorrect) {
                feedback += '<p style="color: var(--secondary-color);">❌ Seu entendimento do motivo está incompleto.</p>';
            } else {
                feedback += '<p style="color: var(--accent-green);">✓ Você identificou o motivo corretamente!</p>';
            }

            if (!result.methodCorrect) {
                feedback += '<p style="color: var(--secondary-color);">❌ Sua explicação do método não corresponde às evidências.</p>';
            } else {
                feedback += '<p style="color: var(--accent-green);">✓ Você identificou o método corretamente!</p>';
            }

            contentElement.innerHTML = feedback;
        }

        this.showModal('result-modal');
    }

    showNotification(message, type = 'info') {
        // Create a simple toast notification
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? 'var(--accent-green)' : type === 'error' ? 'var(--accent-red)' : 'var(--primary-color)'};
            color: var(--text-light);
            padding: 15px 25px;
            border-radius: 8px;
            border: 2px solid var(--border-color);
            box-shadow: 0 4px 15px var(--shadow);
            z-index: 10000;
            animation: slideIn 0.3s ease;
            max-width: 400px;
        `;
        notification.textContent = message;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(400px)';
            notification.style.transition = 'all 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Initialize the game when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.uiController = new UIController();
});
