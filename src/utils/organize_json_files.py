# Conteúdo do arquivo organize_json_files.py
# src/utils/organize_json_files.py
import os
import sys
import json
import shutil
from pathlib import Path

def copy_files():
    """Copia arquivos JSON para os diretórios corretos"""
    print("Organizando arquivos JSON para o Enigma Hunter...")
    
    # Obtenha o diretório base
    base_dir = Path(__file__).resolve().parent.parent.parent
    
    # Diretório fonte dos documentos
    source_dir = base_dir / "docs"
    if not source_dir.exists():
        source_dir = base_dir
    
    # Diretório de destino da história
    story_dir = base_dir / "historias" / "o_segredo_da_estalagem_do_cervo_negro"
    story_dir.mkdir(exist_ok=True, parents=True)
    
    # Criar subdiretórios
    ambientes_dir = story_dir / "ambientes"
    personagens_dir = story_dir / "personagens"
    data_dir = story_dir / "data"
    
    for d in [ambientes_dir, personagens_dir, data_dir]:
        d.mkdir(exist_ok=True)
    
    # Procurar arquivos JSON relevantes
    files_copied = 0
    
    # Copia historia_base.json
    historia_base_files = list(source_dir.glob("**/historia_base.json"))
    if historia_base_files:
        shutil.copy(historia_base_files[0], story_dir)
        print(f"✓ Copiado: {historia_base_files[0].name} para {story_dir}")
        files_copied += 1
    else:
        # Verificar se há otro arquivo que poderia ser a história base
        potential_base = list(source_dir.glob("**/historia_base*")) or list(source_dir.glob("**/Descrição Geral.txt"))
        if potential_base:
            # Converter para formato JSON se necessário
            if potential_base[0].suffix != ".json":
                with open(potential_base[0], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                base_data = {
                    "title": "O Segredo da Estalagem do Cervo Negro",
                    "description": content[:500],  # Primeiros 500 caracteres como descrição
                    "introduction": content,
                    "conclusion": "",
                    "difficulty_level": 3,
                    "solution_criteria": {}
                }
                
                with open(story_dir / "historia_base.json", 'w', encoding='utf-8') as f:
                    json.dump(base_data, f, ensure_ascii=False, indent=2)
                
                print(f"✓ Criado: historia_base.json baseado em {potential_base[0].name}")
                files_copied += 1
    
    # Copia arquivos de ambiente
    ambiente_files = list(source_dir.glob("**/Ambiente_*.json"))
    for file in ambiente_files:
        shutil.copy(file, ambientes_dir)
        print(f"✓ Copiado: {file.name} para {ambientes_dir}")
        files_copied += 1
    
    # Copia arquivos de personagem
    personagem_files = list(source_dir.glob("**/Personagem_*.json"))
    for file in personagem_files:
        shutil.copy(file, personagens_dir)
        print(f"✓ Copiado: {file.name} para {personagens_dir}")
        files_copied += 1
    
    # Copia arquivos de dados
    data_files = []
    for pattern in ["objetos.json", "pistas.json", "qrcodes.json", "sistema-especializacao.json"]:
        data_files.extend(list(source_dir.glob(f"**/{pattern}")))
    
    for file in data_files:
        shutil.copy(file, data_dir)
        print(f"✓ Copiado: {file.name} para {data_dir}")
        files_copied += 1
    
    print(f"\nTotal de {files_copied} arquivos copiados para a estrutura do Enigma Hunter.")
    print(f"Estrutura de diretórios organizada em: {story_dir}")

if __name__ == "__main__":
    copy_files()