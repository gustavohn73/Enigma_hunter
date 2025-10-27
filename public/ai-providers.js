// AI Providers System - Suporte para múltiplas APIs de IA
class AIProviderManager {
    constructor() {
        this.currentProvider = localStorage.getItem('enigma_ai_provider') || 'gemini';
        this.config = this.loadConfig();
        this.functions = window.firebaseServices?.functions;
    }

    loadConfig() {
        const savedConfig = localStorage.getItem('enigma_ai_config');
        return savedConfig ? JSON.parse(savedConfig) : {
            gemini: { apiKey: '', model: 'gemini-pro' },
            openai: { apiKey: '', model: 'gpt-3.5-turbo' },
            claude: { apiKey: '', model: 'claude-3-haiku-20240307' },
            deepseek: { apiKey: '', model: 'deepseek-chat' },
            ollama: { baseUrl: 'http://localhost:11434', model: 'llama3' },
            perplexity: { apiKey: '', model: 'llama-3.1-sonar-small-128k-online' }
        };
    }

    saveConfig() {
        localStorage.setItem('enigma_ai_config', JSON.stringify(this.config));
    }

    setProvider(provider) {
        this.currentProvider = provider;
        localStorage.setItem('enigma_ai_provider', provider);
    }

    getProvider() {
        return this.currentProvider;
    }

    updateProviderConfig(provider, config) {
        this.config[provider] = { ...this.config[provider], ...config };
        this.saveConfig();
    }

    getProviderConfig(provider) {
        return this.config[provider || this.currentProvider];
    }

    // Lista de providers disponíveis
    getAvailableProviders() {
        return [
            {
                id: 'gemini',
                name: 'Google Gemini',
                description: 'API gratuita do Google (60 req/min)',
                free: true,
                needsKey: true,
                setupUrl: 'https://makersuite.google.com/app/apikey'
            },
            {
                id: 'ollama',
                name: 'Ollama (Local)',
                description: 'IA local rodando na sua máquina',
                free: true,
                needsKey: false,
                setupUrl: 'https://ollama.ai/download'
            },
            {
                id: 'openai',
                name: 'OpenAI GPT',
                description: 'ChatGPT API (pago)',
                free: false,
                needsKey: true,
                setupUrl: 'https://platform.openai.com/api-keys'
            },
            {
                id: 'claude',
                name: 'Anthropic Claude',
                description: 'Claude API (pago)',
                free: false,
                needsKey: true,
                setupUrl: 'https://console.anthropic.com/account/keys'
            },
            {
                id: 'deepseek',
                name: 'DeepSeek',
                description: 'DeepSeek API (preços baixos)',
                free: false,
                needsKey: true,
                setupUrl: 'https://platform.deepseek.com/api_keys'
            },
            {
                id: 'perplexity',
                name: 'Perplexity',
                description: 'Perplexity API',
                free: false,
                needsKey: true,
                setupUrl: 'https://www.perplexity.ai/settings/api'
            }
        ];
    }

    // Verificar se o provider está configurado
    async isProviderReady(provider = this.currentProvider) {
        const config = this.getProviderConfig(provider);

        switch (provider) {
            case 'ollama':
                return await this.checkOllamaAvailability();

            case 'gemini':
            case 'openai':
            case 'claude':
            case 'deepseek':
            case 'perplexity':
                return !!config.apiKey;

            default:
                return false;
        }
    }

    async checkOllamaAvailability() {
        try {
            const config = this.getProviderConfig('ollama');
            const response = await fetch(`${config.baseUrl}/api/tags`);
            return response.ok;
        } catch (error) {
            return false;
        }
    }

    // Gerar texto com o provider atual
    async generateText(prompt, systemPrompt, options = {}) {
        const provider = this.currentProvider;
        const config = this.getProviderConfig(provider);

        try {
            switch (provider) {
                case 'gemini':
                    return await this.generateWithGemini(prompt, systemPrompt, config, options);

                case 'ollama':
                    return await this.generateWithOllama(prompt, systemPrompt, config, options);

                case 'openai':
                    return await this.generateWithOpenAI(prompt, systemPrompt, config, options);

                case 'claude':
                    return await this.generateWithClaude(prompt, systemPrompt, config, options);

                case 'deepseek':
                    return await this.generateWithDeepSeek(prompt, systemPrompt, config, options);

                case 'perplexity':
                    return await this.generateWithPerplexity(prompt, systemPrompt, config, options);

                default:
                    throw new Error(`Provider ${provider} not supported`);
            }
        } catch (error) {
            console.error(`Error with ${provider}:`, error);
            throw error;
        }
    }

    // Implementação para Gemini (GRATUITO!)
    async generateWithGemini(prompt, systemPrompt, config, options) {
        if (!config.apiKey) {
            throw new Error('Gemini API key not configured');
        }

        const fullPrompt = systemPrompt ? `${systemPrompt}\n\n${prompt}` : prompt;

        const response = await fetch(
            `https://generativelanguage.googleapis.com/v1beta/models/${config.model}:generateContent?key=${config.apiKey}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contents: [{
                        parts: [{ text: fullPrompt }]
                    }],
                    generationConfig: {
                        temperature: options.temperature || 0.7,
                        maxOutputTokens: options.maxTokens || 1024,
                        topP: options.topP || 0.9
                    }
                })
            }
        );

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Gemini API error: ${error}`);
        }

        const data = await response.json();
        return data.candidates[0]?.content?.parts[0]?.text || '';
    }

    // Implementação para Ollama (LOCAL - GRATUITO!)
    async generateWithOllama(prompt, systemPrompt, config, options) {
        const fullPrompt = systemPrompt ? `${systemPrompt}\n\n${prompt}` : prompt;

        const response = await fetch(`${config.baseUrl}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: config.model,
                prompt: fullPrompt,
                stream: false,
                options: {
                    temperature: options.temperature || 0.7,
                    top_p: options.topP || 0.9,
                    num_predict: options.maxTokens || 1024
                }
            })
        });

        if (!response.ok) {
            throw new Error('Ollama not available. Make sure Ollama is running.');
        }

        const data = await response.json();
        return data.response;
    }

    // Implementação para OpenAI
    async generateWithOpenAI(prompt, systemPrompt, config, options) {
        if (!config.apiKey) {
            throw new Error('OpenAI API key not configured');
        }

        const messages = [];
        if (systemPrompt) {
            messages.push({ role: 'system', content: systemPrompt });
        }
        messages.push({ role: 'user', content: prompt });

        const response = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${config.apiKey}`
            },
            body: JSON.stringify({
                model: config.model,
                messages: messages,
                temperature: options.temperature || 0.7,
                max_tokens: options.maxTokens || 1024
            })
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`OpenAI API error: ${error}`);
        }

        const data = await response.json();
        return data.choices[0]?.message?.content || '';
    }

    // Implementação para Claude
    async generateWithClaude(prompt, systemPrompt, config, options) {
        if (!config.apiKey) {
            throw new Error('Claude API key not configured');
        }

        const response = await fetch('https://api.anthropic.com/v1/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': config.apiKey,
                'anthropic-version': '2023-06-01'
            },
            body: JSON.stringify({
                model: config.model,
                max_tokens: options.maxTokens || 1024,
                system: systemPrompt,
                messages: [{
                    role: 'user',
                    content: prompt
                }],
                temperature: options.temperature || 0.7
            })
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Claude API error: ${error}`);
        }

        const data = await response.json();
        return data.content[0]?.text || '';
    }

    // Implementação para DeepSeek
    async generateWithDeepSeek(prompt, systemPrompt, config, options) {
        if (!config.apiKey) {
            throw new Error('DeepSeek API key not configured');
        }

        const messages = [];
        if (systemPrompt) {
            messages.push({ role: 'system', content: systemPrompt });
        }
        messages.push({ role: 'user', content: prompt });

        const response = await fetch('https://api.deepseek.com/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${config.apiKey}`
            },
            body: JSON.stringify({
                model: config.model,
                messages: messages,
                temperature: options.temperature || 0.7,
                max_tokens: options.maxTokens || 1024
            })
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`DeepSeek API error: ${error}`);
        }

        const data = await response.json();
        return data.choices[0]?.message?.content || '';
    }

    // Implementação para Perplexity
    async generateWithPerplexity(prompt, systemPrompt, config, options) {
        if (!config.apiKey) {
            throw new Error('Perplexity API key not configured');
        }

        const messages = [];
        if (systemPrompt) {
            messages.push({ role: 'system', content: systemPrompt });
        }
        messages.push({ role: 'user', content: prompt });

        const response = await fetch('https://api.perplexity.ai/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${config.apiKey}`
            },
            body: JSON.stringify({
                model: config.model,
                messages: messages,
                temperature: options.temperature || 0.7,
                max_tokens: options.maxTokens || 1024
            })
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Perplexity API error: ${error}`);
        }

        const data = await response.json();
        return data.choices[0]?.message?.content || '';
    }
}

// Make available globally
window.AIProviderManager = AIProviderManager;
