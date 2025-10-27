const admin = require('firebase-admin');

class FirebaseConfig {
    constructor() {
        this.environment = this.detectEnvironment();
        this.initialized = false;
    }

    detectEnvironment() {
        const args = process.argv.slice(2);

        if (args.includes('--production') || args.includes('--prod')) {
            return 'production';
        }

        if (process.env.FIRESTORE_EMULATOR_HOST || args.includes('--emulator')) {
            return 'emulator';
        }

        return 'emulator';
    }

    initialize() {
        if (this.initialized) {
            console.warn('Firebase já inicializado');
            return;
        }

        console.log(`\n🔧 Inicializando Firebase em modo: ${this.environment.toUpperCase()}\n`);

        if (this.environment === 'production') {
            this.initializeProduction();
        } else {
            this.initializeEmulator();
        }

        this.initialized = true;
    }

    initializeProduction() {
        try {
            const serviceAccount = require('../service-account-key.json');

            admin.initializeApp({
                credential: admin.credential.cert(serviceAccount)
            });

            console.log('✓ Conectado ao Firebase PRODUÇÃO');
            console.log(`✓ Projeto: ${serviceAccount.project_id}\n`);
        } catch (error) {
            console.error('❌ Erro ao inicializar produção:');
            console.error('   Certifique-se de ter o arquivo service-account-key.json na raiz do projeto');
            console.error('   Obtenha em: Firebase Console → Configurações → Contas de serviço\n');
            process.exit(1);
        }
    }

    initializeEmulator() {
        process.env.FIRESTORE_EMULATOR_HOST = 'localhost:8080';

        admin.initializeApp({
            projectId: 'demo-enigma-hunter'
        });

        console.log('✓ Conectado ao Emulator LOCAL');
        console.log('✓ Host: localhost:8080');
        console.log('✓ Certifique-se de que os emulators estão rodando: firebase emulators:start\n');
    }

    getDb() {
        if (!this.initialized) {
            throw new Error('Firebase não inicializado. Chame initialize() primeiro.');
        }
        return admin.firestore();
    }

    isProduction() {
        return this.environment === 'production';
    }
}

module.exports = new FirebaseConfig();