# src/data_loader.py
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

class DataLoader:
    """
    Classe responsável por carregar todos os dados do jogo
    incluindo histórias, ambientes, personagens, objetos e pistas.
    """
    
    def __init__(self, base_path: str = ""):
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.data = {
            "historias": {},
            "ambientes": {},
            "personagens": {},
            "objetos": [],
            "pistas": [],
            "qrcodes": [],
            "especializacao": {}
        }
        
        # Inicializa o mapeamento para pesquisa rápida
        self.id_mapping = {
            "ambiente": {},      
            "area": {},          
            "personagem": {},    
            "objeto": {},        
            "pista": {},         
            "qrcode": {},        
            "especializacao": {} 
        }
    
    def carregar_historia(self, nome_historia: str) -> Dict:
        
        """
        Carrega os dados da história especificada
        """

        historia_path = self.base_path / "historias" / nome_historia / "historia_base.json"
        if not historia_path.exists():
            raise FileNotFoundError(f"História não encontrada: {historia_path}")
        
        with open(historia_path, 'r', encoding='utf-8') as file:
            historia_data = json.load(file)
            
        self.data["historias"][nome_historia] = historia_data
        
        # Carrega todos os componentes da história
        self._carregar_ambientes(nome_historia)
        self._carregar_personagens(nome_historia)
        self._carregar_objetos_pistas(nome_historia)
        self._carregar_qrcodes(nome_historia)
        self._carregar_sistema_especializacao(nome_historia) 
        
        # Constrói as referências cruzadas para consulta rápida
        self._construir_mapeamento_ids()
        
        return historia_data
    
    def _carregar_sistema_especializacao(self, nome_historia: str) -> None:
        """
        🆕 Carrega os dados do sistema de especialização da história.
        """
        especializacao_path = self.base_path / "data" / "sistema-especializacao.json"

        if not especializacao_path.exists():
            print(f"Aviso: Arquivo de especialização não encontrado: {especializacao_path}")
            return

        try:
            with open(especializacao_path, 'r', encoding='utf-8') as file:
                self.data["especializacao"] = json.load(file)

            # Criar um mapeamento para acesso rápido
            for categoria in self.data["especializacao"].get("categorias", []):
                self.id_mapping["especializacao"][categoria["id"]] = categoria

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Erro ao carregar especialização: {e}")

    def get_especializacao(self, categoria_id: str) -> Optional[Dict]:
        """
        🆕 Retorna os dados de especialização para uma categoria específica.
        """
        return self.id_mapping["especializacao"].get(categoria_id)

    def verificar_requisitos_especializacao(self, categoria_id: str, nivel: int) -> bool:
        """
        🆕 Verifica se um jogador atende aos requisitos de especialização.
        """
        categoria = self.get_especializacao(categoria_id)
        if not categoria:
            return False

        requisitos = categoria.get("niveis", {})
        return nivel >= min(map(int, requisitos.keys()), default=0)

    def listar_especializacoes(self) -> List[Dict]:
        """
        🆕 Retorna todas as categorias de especialização disponíveis.
        """
        return list(self.id_mapping["especializacao"].values())
    
    def _carregar_ambientes(self, nome_historia: str) -> None:
        """Carrega todos os ambientes da história"""
        ambientes_dir = self.base_path / "historias" / nome_historia / "ambientes"
        
        if not ambientes_dir.exists():
            print(f"Aviso: Diretório de ambientes não encontrado: {ambientes_dir}")
            return
        
        ambientes = {}
        
        for arquivo in ambientes_dir.glob("Ambiente_*.json"):
            with open(arquivo, 'r', encoding='utf-8') as file:
                ambiente_data = json.load(file)
                # Supõe que ambiente_data é uma lista e pega o primeiro item
                if isinstance(ambiente_data, list) and ambiente_data:
                    for amb in ambiente_data:
                        ambiente_id = amb.get("location_id")
                        if ambiente_id:
                            ambientes[ambiente_id] = amb
                # Ou se for diretamente um objeto
                elif isinstance(ambiente_data, dict) and "location_id" in ambiente_data:
                    ambiente_id = ambiente_data["location_id"]
                    ambientes[ambiente_id] = ambiente_data
        
        self.data["ambientes"][nome_historia] = ambientes
    
    def _carregar_personagens(self, nome_historia: str) -> None:
        """Carrega todos os personagens da história"""
        personagens_dir = self.base_path / "historias" / nome_historia / "personagens"
        
        if not personagens_dir.exists():
            print(f"Aviso: Diretório de personagens não encontrado: {personagens_dir}")
            return
        
        personagens = {}
        
        for arquivo in personagens_dir.glob("Personagem_*.json"):
            with open(arquivo, 'r', encoding='utf-8') as file:
                personagem_data = json.load(file)
                # Supõe que personagem_data é uma lista e pega o primeiro item
                if isinstance(personagem_data, list) and personagem_data:
                    for pers in personagem_data:
                        personagem_id = pers.get("character_id")
                        if personagem_id:
                            personagens[personagem_id] = pers
                # Ou se for diretamente um objeto
                elif isinstance(personagem_data, dict) and "character_id" in personagem_data:
                    personagem_id = personagem_data["character_id"]
                    personagens[personagem_id] = personagem_data
        
        self.data["personagens"][nome_historia] = personagens
    
    def _carregar_objetos_pistas(self, nome_historia: str) -> None:
        """Carrega objetos e pistas da história"""
        data_dir = self.base_path / "historias" / nome_historia / "data"
        
        # Carrega objetos
        objetos_path = data_dir / "objetos.json"
        if objetos_path.exists():
            with open(objetos_path, 'r', encoding='utf-8') as file:
                self.data["objetos"] = json.load(file)
        
        # Carrega pistas
        pistas_path = data_dir / "pistas.json"
        if pistas_path.exists():
            with open(pistas_path, 'r', encoding='utf-8') as file:
                self.data["pistas"] = json.load(file)
    
    def _carregar_qrcodes(self, nome_historia: str) -> None:
        """Carrega dados de QR codes da história"""
        data_dir = self.base_path / "historias" / nome_historia / "data"
        
        qrcodes_path = data_dir / "qrcodes.json"
        if qrcodes_path.exists():
            with open(qrcodes_path, 'r', encoding='utf-8') as file:
                self.data["qrcodes"] = json.load(file)
    
    def _construir_mapeamento_ids(self) -> None:
        """Constrói o mapeamento de IDs para pesquisa rápida"""
        # Mapeia ambientes
        for historia, ambientes in self.data["ambientes"].items():
            for ambiente_id, ambiente in ambientes.items():
                self.id_mapping["ambiente"][ambiente_id] = ambiente
                
                # Mapeia áreas dentro do ambiente
                if "areas" in ambiente:
                    for area in ambiente["areas"]:
                        area_id = area.get("area_id")
                        if area_id:
                            self.id_mapping["area"][area_id] = area
        
        # Mapeia personagens
        for historia, personagens in self.data["personagens"].items():
            for personagem_id, personagem in personagens.items():
                self.id_mapping["personagem"][personagem_id] = personagem
        
        # Mapeia objetos
        for objeto in self.data["objetos"]:
            objeto_id = objeto.get("object_id")
            if objeto_id:
                self.id_mapping["objeto"][objeto_id] = objeto
        
        # Mapeia pistas
        for pista in self.data["pistas"]:
            pista_id = pista.get("clue_id")
            if pista_id:
                self.id_mapping["pista"][pista_id] = pista
        
        # Mapeia QR codes
        for qrcode in self.data["qrcodes"]:
            uuid = qrcode.get("uuid")
            if uuid:
                self.id_mapping["qrcode"][uuid] = qrcode
    
    def get_ambiente(self, ambiente_id: int) -> Optional[Dict]:
        """Retorna os dados de um ambiente pelo ID"""
        return self.id_mapping["ambiente"].get(ambiente_id)
    
    def get_area(self, area_id: int) -> Optional[Dict]:
        """Retorna os dados de uma área pelo ID"""
        return self.id_mapping["area"].get(area_id)
    
    def get_personagem(self, personagem_id: int) -> Optional[Dict]:
        """Retorna os dados de um personagem pelo ID"""
        return self.id_mapping["personagem"].get(personagem_id)
    
    def get_objeto(self, objeto_id: int) -> Optional[Dict]:
        """Retorna os dados de um objeto pelo ID"""
        return self.id_mapping["objeto"].get(objeto_id)
    
    def get_pista(self, pista_id: int) -> Optional[Dict]:
        """Retorna os dados de uma pista pelo ID"""
        return self.id_mapping["pista"].get(pista_id)
    
    def get_qrcode(self, uuid: str) -> Optional[Dict]:
        """Retorna os dados de um QR code pelo UUID"""
        return self.id_mapping["qrcode"].get(uuid)

# Exemplo de uso
if __name__ == "__main__":
    loader = DataLoader()
    try:
        historia = loader.carregar_historia("estalagem_cervo_negro")
        print(f"História carregada: {historia['title']}")
        
        # Exemplo de acesso aos dados
        print(f"Número de ambientes: {len(loader.data['ambientes']['estalagem_cervo_negro'])}")
        print(f"Número de personagens: {len(loader.data['personagens']['estalagem_cervo_negro'])}")
        print(f"Número de objetos: {len(loader.data['objetos'])}")
        print(f"Número de pistas: {len(loader.data['pistas'])}")
        print(f"Número de QR codes: {len(loader.data['qrcodes'])}")
        
    except FileNotFoundError as e:
        print(f"Erro ao carregar história: {e}")
