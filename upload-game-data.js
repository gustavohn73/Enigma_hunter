#!/usr/bin/env node

const path = require('path');
const readline = require('readline');
const firebaseConfig = require('./scripts/firebase-config');
const DataUploader = require('./scripts/data-uploader');

const HISTORIA_PATH = './historias/o_segredo_da_estalagem_do_cervo_negro';

function showUsage() {
    console.log(`
📦 Upload de Dados do Jogo - Enigma Hunter

Uso:
  node upload-game-data.js [opções]

Opções:
  --emulator, --dev         Upload para emulator local (padrão)
  --production, --prod      Upload para produção (requer service-account-key.json)
  --help, -h                Mostrar esta ajuda

Exemplos:
  node upload-game-data.js                    # Upload para emulator
  node upload-game-data.js --emulator         # Upload para emulator
  node upload-game-data.js --production       # Upload para produção

Para desenvolvimento:
  1. Inicie os emulators: firebase emulators:start
  2. Execute: npm run upload-data

Para produção:
  1. Obtenha service-account-key.json do Firebase Console
  2. Execute: npm run upload-data:production
  `);
}

async function confirmProduction() {
    if (!firebaseConfig.isProduction()) {
        return true;
    }

    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    return new Promise((resolve) => {
        console.log('\n⚠️  ATENÇÃO: Você está prestes a fazer upload para PRODUÇÃO!\n');
        rl.question('Deseja continuar? (sim/não): ', (answer) => {
            rl.close();
            const confirmed = answer.toLowerCase() === 'sim' || answer.toLowerCase() === 's';
            if (!confirmed) {
                console.log('\n❌ Upload cancelado pelo usuário\n');
            }
            resolve(confirmed);
        });
    });
}

async function main() {
    const args = process.argv.slice(2);

    if (args.includes('--help') || args.includes('-h')) {
        showUsage();
        process.exit(0);
    }

    console.log('═══════════════════════════════════════════════════════');
    console.log('  🎮 Upload de Dados - Enigma Hunter');
    console.log('═══════════════════════════════════════════════════════');

    firebaseConfig.initialize();

    const confirmed = await confirmProduction();
    if (!confirmed) {
        process.exit(0);
    }

    const db = firebaseConfig.getDb();
    const uploader = new DataUploader(db, HISTORIA_PATH);

    const success = await uploader.uploadAll();

    if (success) {
        console.log('\n📍 Próximos passos:');
        if (firebaseConfig.isProduction()) {
            console.log('   1. Execute: npm run deploy');
            console.log('   2. Acesse: https://seu-projeto.web.app\n');
        } else {
            console.log('   1. Acesse: http://localhost:5000');
            console.log('   2. Comece a jogar!\n');
        }
        process.exit(0);
    } else {
        process.exit(1);
    }
}

main().catch(error => {
    console.error('\n❌ Erro fatal:', error);
    process.exit(1);
});