#!/usr/bin/env node

/**
 * Script to upload game data to Firestore
 * Run with: node upload-game-data.js
 *
 * Make sure you have:
 * 1. Firebase CLI installed: npm install -g firebase-tools
 * 2. Logged in: firebase login
 * 3. Project configured: firebase use --add
 */

const admin = require('firebase-admin');
const fs = require('fs');
const path = require('path');

// Initialize Firebase Admin
// For local testing, you can use emulator
// For production, make sure you have proper credentials

// Uncomment for production (requires service account key):
// const serviceAccount = require('./path-to-service-account-key.json');
// admin.initializeApp({
//   credential: admin.credential.cert(serviceAccount)
// });

// For emulator:
process.env.FIRESTORE_EMULATOR_HOST = 'localhost:8080';
admin.initializeApp({
  projectId: 'enigma-hunter'
});

const db = admin.firestore();

// Paths
const HISTORIA_PATH = './historias/o_segredo_da_estalagem_do_cervo_negro';

/**
 * Read JSON file
 */
function readJSON(filePath) {
  try {
    const data = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error(`Error reading ${filePath}:`, error.message);
    return null;
  }
}

/**
 * Upload historia_base
 */
async function uploadHistoriaBase() {
  console.log('Uploading historia_base...');
  const data = readJSON(path.join(HISTORIA_PATH, 'historia_base.json'));

  if (!data) {
    console.error('Failed to read historia_base.json');
    return;
  }

  await db.collection('game_data').doc('historia_base').set(data);
  console.log('✓ historia_base uploaded');
}

/**
 * Upload ambientes (locations)
 */
async function uploadAmbientes() {
  console.log('Uploading ambientes...');
  const ambientesDir = path.join(HISTORIA_PATH, 'ambientes');
  const files = fs.readdirSync(ambientesDir).filter(f => f.endsWith('.json'));

  const allAmbientes = {};

  for (const file of files) {
    const filePath = path.join(ambientesDir, file);
    const data = readJSON(filePath);

    if (data && Array.isArray(data)) {
      data.forEach(location => {
        allAmbientes[location.location_id] = location;
      });
    }
  }

  await db.collection('game_data').doc('ambientes').set(allAmbientes);
  console.log(`✓ ${Object.keys(allAmbientes).length} ambientes uploaded`);
}

/**
 * Upload personagens (characters)
 */
async function uploadPersonagens() {
  console.log('Uploading personagens...');
  const personagensDir = path.join(HISTORIA_PATH, 'personagens');
  const files = fs.readdirSync(personagensDir).filter(f => f.endsWith('.json'));

  const allPersonagens = {};

  for (const file of files) {
    const filePath = path.join(personagensDir, file);
    const data = readJSON(filePath);

    if (data && Array.isArray(data)) {
      data.forEach(character => {
        allPersonagens[character.character_id] = character;
      });
    }
  }

  await db.collection('game_data').doc('personagens').set(allPersonagens);
  console.log(`✓ ${Object.keys(allPersonagens).length} personagens uploaded`);
}

/**
 * Upload objetos
 */
async function uploadObjetos() {
  console.log('Uploading objetos...');
  const data = readJSON(path.join(HISTORIA_PATH, 'data/objetos.json'));

  if (!data) {
    console.error('Failed to read objetos.json');
    return;
  }

  await db.collection('game_data').doc('objetos').set({
    items: data
  });
  console.log(`✓ ${data.length} objetos uploaded`);
}

/**
 * Upload pistas (clues)
 */
async function uploadPistas() {
  console.log('Uploading pistas...');
  const data = readJSON(path.join(HISTORIA_PATH, 'data/pistas.json'));

  if (!data) {
    console.error('Failed to read pistas.json');
    return;
  }

  await db.collection('game_data').doc('pistas').set({
    items: data
  });
  console.log(`✓ ${data.length} pistas uploaded`);
}

/**
 * Upload sistema de especialização
 */
async function uploadSistemaEspecializacao() {
  console.log('Uploading sistema_especializacao...');
  const data = readJSON(path.join(HISTORIA_PATH, 'data/sistema-especializacao.json'));

  if (!data) {
    console.error('Failed to read sistema-especializacao.json');
    return;
  }

  await db.collection('game_data').doc('sistema_especializacao').set(data);
  console.log('✓ sistema_especializacao uploaded');
}

/**
 * Main function
 */
async function main() {
  console.log('Starting game data upload to Firestore...\n');

  try {
    await uploadHistoriaBase();
    await uploadAmbientes();
    await uploadPersonagens();
    await uploadObjetos();
    await uploadPistas();
    await uploadSistemaEspecializacao();

    console.log('\n✓ All game data uploaded successfully!');
    console.log('\nYou can now start the game with: firebase emulators:start');

  } catch (error) {
    console.error('\n✗ Error uploading game data:', error);
  } finally {
    process.exit(0);
  }
}

// Run main function
main();
