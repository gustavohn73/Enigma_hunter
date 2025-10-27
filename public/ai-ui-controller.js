// AI UI Controller - Gerencia interfaces de IA e geração de histórias
class AIUIController {
    constructor(uiController) {
        this.uiController = uiController;
        this.aiProvider = new AIProviderManager();
        this.storyGenerator = new StoryGenerator(this.aiProvider);
        this.setupEventListeners();
        this.checkAIStatus();
    }

    setupEventListeners() {
        // AI Settings
        document.getElementById('btn-ai-settings').addEventListener('click', () => this.showAISettings());
        document.getElementById('btn-close-ai-settings').addEventListener('click', () => this.hideModal('ai-settings-modal'));
        document.getElementById('btn-save-ai-settings').addEventListener('click', () => this.saveAISettings());
        document.getElementById('btn-test-ai').addEventListener('click', () => this.testAIConnection());

        // Story Generator
        document.getElementById('btn-create-story').addEventListener('click', () => this.showStoryGenerator());
        document.getElementById('btn-cancel-story-gen').addEventListener('click', () => this.hideModal('story-generator-modal'));
        document.getElementById('btn-generate-story').addEventListener('click', () => this.generateStory());

        // Story theme selector
        document.getElementById('story-theme').addEventListener('change', (e) => {
            const customGroup = document.getElementById('custom-theme-group');
            customGroup.classList.toggle('hidden', e.target.value !== 'custom');
        });
    }

    async checkAIStatus() {
        const isReady = await this.aiProvider.isProviderReady();
        if (!isReady) {
            console.warn('AI provider not configured');
        }
    }

    showAISettings() {
        this.showModal('ai-settings-modal');
        this.renderProviderList();
        this.renderProviderConfig();
    }

    renderProviderList() {
        const listElement = document.getElementById('provider-list');
        listElement.innerHTML = '';

        const providers = this.aiProvider.getAvailableProviders();
        const currentProvider = this.aiProvider.getProvider();

        providers.forEach(provider => {
            const card = document.createElement('div');
            card.className = `provider-card ${provider.free ? 'free' : ''} ${provider.id === currentProvider ? 'selected' : ''}`;
            card.innerHTML = `
                <h4>${provider.name}</h4>
                <p>${provider.description}</p>
                ${provider.needsKey ? '<p style="font-size: 0.85rem; opacity: 0.7;">Requer API key</p>' : ''}
            `;
            card.addEventListener('click', () => {
                this.aiProvider.setProvider(provider.id);
                this.renderProviderList();
                this.renderProviderConfig();
            });
            listElement.appendChild(card);
        });
    }

    renderProviderConfig() {
        const configElement = document.getElementById('config-fields');
        configElement.innerHTML = '';

        const currentProvider = this.aiProvider.getProvider();
        const providers = this.aiProvider.getAvailableProviders();
        const providerInfo = providers.find(p => p.id === currentProvider);
        const config = this.aiProvider.getProviderConfig();

        if (currentProvider === 'ollama') {
            // Ollama configuration
            configElement.innerHTML = `
                <div class="config-field">
                    <label>URL do Ollama:</label>
                    <input type="text" id="ollama-url" value="${config.baseUrl}" placeholder="http://localhost:11434">
                    <small>Certifique-se de que o Ollama está rodando localmente</small>
                </div>
                <div class="config-field">
                    <label>Modelo:</label>
                    <input type="text" id="ollama-model" value="${config.model}" placeholder="llama3">
                    <small>Nome do modelo instalado no Ollama</small>
                </div>
            `;
        } else if (providerInfo && providerInfo.needsKey) {
            // API key configuration
            configElement.innerHTML = `
                <div class="config-field">
                    <label>API Key:</label>
                    <input type="password" id="api-key" value="${config.apiKey || ''}" placeholder="sk-...">
                    <small>Obtenha sua API key em: <a href="${providerInfo.setupUrl}" target="_blank">Clique aqui</a></small>
                </div>
                <div class="config-field">
                    <label>Modelo:</label>
                    <input type="text" id="api-model" value="${config.model}" placeholder="${config.model}">
                    <small>Nome do modelo a ser usado</small>
                </div>
            `;
        }
    }

    saveAISettings() {
        const currentProvider = this.aiProvider.getProvider();

        if (currentProvider === 'ollama') {
            const baseUrl = document.getElementById('ollama-url').value;
            const model = document.getElementById('ollama-model').value;
            this.aiProvider.updateProviderConfig('ollama', { baseUrl, model });
        } else {
            const apiKey = document.getElementById('api-key').value;
            const model = document.getElementById('api-model').value;
            this.aiProvider.updateProviderConfig(currentProvider, { apiKey, model });
        }

        this.showNotification('Configurações salvas!', 'success');
    }

    async testAIConnection() {
        const testBtn = document.getElementById('btn-test-ai');
        testBtn.disabled = true;
        testBtn.textContent = 'Testando...';

        try {
            const response = await this.aiProvider.generateText(
                'Responda apenas: "Conexão bem-sucedida!"',
                'Você é um assistente de teste.',
                { maxTokens: 50 }
            );

            if (response) {
                this.showNotification('✓ Conexão bem-sucedida!', 'success');
            } else {
                throw new Error('Empty response');
            }
        } catch (error) {
            console.error('Connection test failed:', error);
            this.showNotification('✗ Erro na conexão: ' + error.message, 'error');
        } finally {
            testBtn.disabled = false;
            testBtn.textContent = 'Testar Conexão';
        }
    }

    async showStoryGenerator() {
        // Verificar se AI está configurada
        const isReady = await this.aiProvider.isProviderReady();
        if (!isReady) {
            const configure = confirm('Você precisa configurar um provider de IA primeiro. Deseja configurar agora?');
            if (configure) {
                this.showAISettings();
            }
            return;
        }

        this.showModal('story-generator-modal');
    }

    async generateStory() {
        const theme = document.getElementById('story-theme').value;
        const customTheme = document.getElementById('custom-theme').value;
        const ageRating = document.getElementById('age-rating').value;
        const difficulty = document.getElementById('difficulty').value;
        const duration = document.getElementById('duration').value;

        const preferences = {
            theme,
            customTheme: theme === 'custom' ? customTheme : null,
            ageRating,
            difficulty,
            duration
        };

        // Mostrar status de geração
        const statusElement = document.getElementById('generation-status');
        const messageElement = document.getElementById('generation-message');
        const generateBtn = document.getElementById('btn-generate-story');

        statusElement.classList.remove('hidden');
        generateBtn.disabled = true;

        try {
            messageElement.textContent = 'Gerando conceito da história...';
            console.log('Starting story generation with preferences:', preferences);

            const story = await this.storyGenerator.generateStory(preferences);

            messageElement.textContent = 'História gerada com sucesso!';

            // Salvar história gerada no Firestore
            await this.saveGeneratedStory(story);

            // Esconder status
            setTimeout(() => {
                statusElement.classList.add('hidden');
                this.hideModal('story-generator-modal');
                this.showNotification('✓ História gerada! Iniciando novo jogo...', 'success');

                // Carregar e iniciar o jogo com a nova história
                this.startGameWithGeneratedStory(story);
            }, 2000);

        } catch (error) {
            console.error('Error generating story:', error);
            messageElement.textContent = 'Erro ao gerar história: ' + error.message;
            this.showNotification('Erro ao gerar história. Verifique suas configurações de IA.', 'error');
            generateBtn.disabled = false;
        }
    }

    async saveGeneratedStory(story) {
        try {
            const storyId = 'generated_' + Date.now();
            const db = window.firebaseServices.db;

            // Salvar em collection separada para histórias geradas
            await db.collection('generated_stories').doc(storyId).set({
                ...story,
                createdAt: new Date().toISOString(),
                storyId: storyId
            });

            console.log('Story saved with ID:', storyId);
            return storyId;
        } catch (error) {
            console.error('Error saving generated story:', error);
            throw error;
        }
    }

    async startGameWithGeneratedStory(story) {
        // Criar novo game engine com a história gerada
        const gameEngine = this.uiController.gameEngine;
        gameEngine.gameData = story;

        // Set initial location
        for (const [locId, location] of Object.entries(story.ambientes)) {
            if (location.is_starting_location) {
                gameEngine.playerState.currentLocation = parseInt(locId);
                if (location.areas && location.areas.length > 0) {
                    gameEngine.playerState.currentArea = location.areas[0].area_id;
                }
                break;
            }
        }

        // Gerar player ID
        const playerId = window.firebaseServices.generateSessionId();
        gameEngine.playerState.playerId = playerId;

        // Salvar o jogo
        await gameEngine.saveGame();

        // Mostrar tela do jogo
        this.uiController.showGameScreen();
    }

    showModal(modalId) {
        document.getElementById(modalId).classList.remove('hidden');
    }

    hideModal(modalId) {
        document.getElementById(modalId).classList.add('hidden');
    }

    showNotification(message, type = 'info') {
        this.uiController.showNotification(message, type);
    }
}

// Make available globally
window.AIUIController = AIUIController;
