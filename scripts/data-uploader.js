const fs = require('fs');
const path = require('path');

class DataUploader {
  constructor(db, historiaPath) {
    this.db = db;
    this.historiaPath = historiaPath;
  }

  readJSON(filePath) {
    try {
      const data = fs.readFileSync(filePath, 'utf8');
      return JSON.parse(data);
    } catch (error) {
      console.error(`❌ Erro ao ler ${filePath}:`, error.message);
      return null;
    }
  }

  async uploadHistoriaBase() {
    console.log('📖 Uploading historia_base...');
    const data = this.readJSON(path.join(this.historiaPath, 'historia_base.json'));

    if (!data) {
      throw new Error('Falha ao ler historia_base.json');
    }

    await this.db.collection('game_data').doc('historia_base').set(data);
    console.log('   ✓ historia_base uploaded');
  }

  async uploadAmbientes() {
    console.log('🗺️  Uploading ambientes...');
    const ambientesDir = path.join(this.historiaPath, 'ambientes');
    
    if (!fs.existsSync(ambientesDir)) {
      throw new Error(`Diretório não encontrado: ${ambientesDir}`);
    }

    const files = fs.readdirSync(ambientesDir).filter(f => f.endsWith('.json'));
    const allAmbientes = {};

    for (const file of files) {
      const filePath = path.join(ambientesDir, file);
      const data = this.readJSON(filePath);

      if (data && Array.isArray(data)) {
        data.forEach(location => {
          allAmbientes[location.location_id] = location;
        });
      }
    }

    await this.db.collection('game_data').doc('ambientes').set(allAmbientes);
    console.log(`   ✓ ${Object.keys(allAmbientes).length} ambientes uploaded`);
  }

  async uploadPersonagens() {
    console.log('👥 Uploading personagens...');
    const personagensDir = path.join(this.historiaPath, 'personagens');
    
    if (!fs.existsSync(personagensDir)) {
      throw new Error(`Diretório não encontrado: ${personagensDir}`);
    }

    const files = fs.readdirSync(personagensDir).filter(f => f.endsWith('.json'));
    const allPersonagens = {};

    for (const file of files) {
      const filePath = path.join(personagensDir, file);
      const data = this.readJSON(filePath);

      if (data && Array.isArray(data)) {
        data.forEach(character => {
          allPersonagens[character.character_id] = character;
        });
      }
    }

    await this.db.collection('game_data').doc('personagens').set(allPersonagens);
    console.log(`   ✓ ${Object.keys(allPersonagens).length} personagens uploaded`);
  }

  async uploadObjetos() {
    console.log('🎒 Uploading objetos...');
    const data = this.readJSON(path.join(this.historiaPath, 'data/objetos.json'));

    if (!data) {
      throw new Error('Falha ao ler objetos.json');
    }

    await this.db.collection('game_data').doc('objetos').set({
      items: data
    });
    console.log(`   ✓ ${data.length} objetos uploaded`);
  }

  async uploadPistas() {
    console.log('🔍 Uploading pistas...');
    const data = this.readJSON(path.join(this.historiaPath, 'data/pistas.json'));

    if (!data) {
      throw new Error('Falha ao ler pistas.json');
    }

    await this.db.collection('game_data').doc('pistas').set({
      items: data
    });
    console.log(`   ✓ ${data.length} pistas uploaded`);
  }

  async uploadSistemaEspecializacao() {
    console.log('⚡ Uploading sistema_especializacao...');
    const data = this.readJSON(path.join(this.historiaPath, 'data/sistema-especializacao.json'));

    if (!data) {
      throw new Error('Falha ao ler sistema-especializacao.json');
    }

    await this.db.collection('game_data').doc('sistema_especializacao').set(data);
    console.log('   ✓ sistema_especializacao uploaded');
  }

  async uploadAll() {
    const startTime = Date.now();

    try {
      await this.uploadHistoriaBase();
      await this.uploadAmbientes();
      await this.uploadPersonagens();
      await this.uploadObjetos();
      await this.uploadPistas();
      await this.uploadSistemaEspecializacao();

      const duration = ((Date.now() - startTime) / 1000).toFixed(2);
      console.log(`\n✅ Todos os dados foram enviados com sucesso! (${duration}s)`);
      
      return true;
    } catch (error) {
      console.error('\n❌ Erro durante upload:', error.message);
      return false;
    }
  }
}

module.exports = DataUploader;