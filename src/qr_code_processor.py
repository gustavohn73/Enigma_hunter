# src/qr_code_processor.py
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

class QRCodeProcessor:
    """
    Processador de QR Codes para o sistema Enigma Hunter
    Suporta múltiplas ações e gatilhos de evolução
    """
    
    # Mapeamento de ações possíveis
    ACOES_SUPORTADAS = {
        'enter': 'processar_entrada',
        'explore': 'processar_exploracao',
        'talk': 'processar_dialogo',
        'collect': 'processar_coleta',
        'examine': 'processar_exame'
    }
    
    def __init__(self, data_loader, game_state_manager):
        self.data_loader = data_loader
        self.game_state_manager = game_state_manager
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Sistema de registro de descobertas
        self.sistema_descobertas = SistemaDescobertasEvolucao()
    
    def processar_qr_code(self, session_id: str, uuid: str) -> Dict[str, Any]:
        """
        Processa um QR Code com verificações avançadas e múltiplas ações
        """
        player_progress = self.game_state_manager.load_session(session_id)
        if not player_progress:
            return {"success": False, "message": "Sessão não encontrada"}
        
        qr_code = self.data_loader.get_qrcode(uuid)
        if not qr_code:
            return {"success": False, "message": "QR Code inválido"}
        
        # Verificação de requisitos com mais detalhes
        resultado_acesso = self.verificar_requisitos_acesso(qr_code, player_progress)
        if not resultado_acesso['access_granted']:
            return {
                "success": False, 
                "message": resultado_acesso['reason']
            }
        
        # Marca QR Code como escaneado
        player_progress.scan_qr_code(uuid)
        
        # Processa ação específica
        metodo_acao = self.ACOES_SUPORTADAS.get(qr_code.get('action'))
        if metodo_acao:
            resultado = getattr(self, metodo_acao)(qr_code, player_progress)
        else:
            resultado = {"success": False, "message": "Ação não suportada"}
        
        # Verifica gatilhos de evolução
        self.verificar_gatilhos_evolucao(qr_code, player_progress)
        
        # Salva progresso
        self.game_state_manager.save_session(session_id)
        
        return resultado
    
    def processar_entrada(self, qr_code: Dict, player_progress) -> Dict:
        """Processa entrada em localização"""
        target_id = qr_code.get('target_id')
        player_progress.enter_location(target_id)
        return {
            "success": True, 
            "message": f"Entrou na localização {target_id}"
        }
    
    def processar_exploracao(self, qr_code: Dict, player_progress) -> Dict:
        """Processa exploração de área"""
        target_id = qr_code.get('target_id')
        player_progress.enter_area(target_id)
        return {
            "success": True, 
            "message": f"Explorou área {target_id}"
        }
    
    def processar_dialogo(self, qr_code: Dict, player_progress) -> Dict:
        """Processa início de diálogo com personagem"""
        character_id = qr_code.get('target_id')
        personagem = self.data_loader.get_personagem(character_id)
        
        if not personagem:
            return {"success": False, "message": "Personagem não encontrado"}
        
        # Lógica de diálogo será implementada posteriormente
        return {
            "success": True, 
            "message": f"Preparando diálogo com {personagem['name']}"
        }
    
    def processar_coleta(self, qr_code: Dict, player_progress) -> Dict:
        """Processa coleta de objeto"""
        object_id = qr_code.get('target_id')
        player_progress.collect_object(object_id)
        return {
            "success": True, 
            "message": f"Coletou objeto {object_id}"
        }
    
    def processar_exame(self, qr_code: Dict, player_progress) -> Dict:
        """Processa exame detalhado de objeto/área"""
        target_id = qr_code.get('target_id')
        target_type = qr_code.get('target_type')
        
        # Recupera detalhes com base no tipo
        if target_type == 'object':
            objeto = self.data_loader.get_objeto(target_id)
            # Adiciona lógica de exame de objeto
        elif target_type == 'area':
            area = self.data_loader.get_area(target_id)
            # Adiciona lógica de exame de área
        
        return {
            "success": True, 
            "message": f"Examinou {target_type} {target_id}"
        }
    
    def verificar_gatilhos_evolucao(self, qr_code: Dict, player_progress):
        """
        Verifica e processa gatilhos de evolução para personagens, objetos, etc.
        """
        target_type = qr_code.get('target_type')
        target_id = qr_code.get('target_id')
        
        # Evolução de personagem
        if target_type == 'character':
            self.sistema_descobertas.evoluir_personagem(
                target_id, 
                player_progress
            )
        
        # Evolução de objeto
        if target_type == 'object':
            self.sistema_descobertas.evoluir_objeto(
                target_id, 
                player_progress
            )
    
    def verificar_requisitos_acesso(self, qr_code: Dict, player_progress) -> Dict:
        """
        Verifica requisitos de acesso com mais detalhes
        """
        # [Código anterior de verificação de requisitos, com melhorias]
        # Adicionar mais verificações contextuais
        
        return {
            "access_granted": True,
            "reason": "Acesso permitido"
        }

class SistemaDescobertasEvolucao:
    """
    Sistema avançado de rastreamento de descobertas e evolução baseado no JSON.
    Evolui personagens conforme os requisitos de gatilho são cumpridos.
    """
    def __init__(self, data_loader):
        self.data_loader = data_loader
        self.logger = logging.getLogger(__name__)

    def evoluir_personagem(self, character_id: int, player_progress):
        """
        Verifica os requisitos no JSON e evolui o personagem se necessário.
        """
        personagem = self.data_loader.get_personagem(character_id)
        if not personagem:
            return

        current_level = player_progress.character_level.get(character_id, 1)
        estagios = personagem.get("estagios", {})

        # Verifica se há um próximo nível disponível
        proximo_nivel = str(current_level + 1)
        if proximo_nivel not in estagios:
            return  # O personagem já está no nível máximo

        # Obtém os gatilhos do próximo nível
        gatilhos = estagios[proximo_nivel].get("triggers", [])

        # Verifica se pelo menos um gatilho foi cumprido
        for gatilho in gatilhos:
            if self._verificar_gatilho(gatilho, player_progress):
                player_progress.update_character_level(character_id, int(proximo_nivel))
                self.logger.info(f"Personagem {character_id} evoluiu para nível {proximo_nivel}")
                return

    def _verificar_gatilho(self, gatilho: Dict[str, Any], player_progress) -> bool:
        """
        Verifica se um gatilho foi acionado de acordo com os requisitos listados.
        """
        requisitos = gatilho.get("requirements", [])
        
        for requisito in requisitos:
            tipo = requisito.get("requirement_type")

            if tipo == "evidence":
                # O jogador precisa ter coletado os objetos necessários como evidência
                objetos_necessarios = set(requisito.get("required_object_id", []))
                if not objetos_necessarios.issubset(player_progress.inventory):
                    return False  # Falha no requisito de evidência

            elif tipo == "specialization":
                # O jogador precisa ter um nível mínimo em uma especialização
                especializacoes = requisito.get("required_specializations", {})
                for cat, nivel_minimo in especializacoes.items():
                    if player_progress.get_specialization_level(cat) < nivel_minimo:
                        return False  # Falha no requisito de especialização

            elif tipo == "location":
                # O jogador precisa estar em uma localização específica
                localizacao_requerida = requisito.get("required_location_id")
                if player_progress.current_location_id != localizacao_requerida:
                    return False  # Falha no requisito de localização

        return True  # Se passou por todas as verificações, o gatilho foi ativado!
    
    
    def evoluir_objeto(self, object_id: int, player_progress):
        """
        Verifica os requisitos no JSON e evolui o objeto se necessário.
        """
        objeto = self.data_loader.get_objeto(object_id)
        if not objeto:
            return

        current_level = player_progress.object_level.get(object_id, 0)
        niveis = objeto.get("levels", [])

        # Verifica se há um próximo nível disponível
        if current_level >= len(niveis) - 1:
            return  # O objeto já está no nível máximo

        proximo_nivel = niveis[current_level + 1]
        requisitos = proximo_nivel.get("requirements", [])

        # Se não há requisitos, o objeto sobe de nível automaticamente
        if not requisitos or self._verificar_requisitos_objeto(requisitos, player_progress):
            player_progress.update_object_level(object_id, current_level + 1)
            self.logger.info(f"Objeto {object_id} evoluiu para nível {current_level + 1}")

    def _verificar_requisitos_objeto(self, requisitos: List[Dict[str, Any]], player_progress) -> bool:
        """
        Verifica se um objeto pode evoluir com base nos requisitos definidos no JSON.
        """

        for requisito in requisitos:
            tipo = requisito.get("requirement_type")

            if tipo == "specialization":
                # O jogador precisa ter um nível mínimo em uma especialização
                especializacoes = requisito.get("required_specializations", {})
                for cat, nivel_minimo in especializacoes.items():
                    if player_progress.get_specialization_level(cat) < nivel_minimo:
                        return False  # Falha no requisito de especialização

            elif tipo == "evidence":
                # O jogador precisa ter coletado objetos específicos como evidência
                objetos_necessarios = set(requisito.get("required_object_id", []))
                if not objetos_necessarios.issubset(player_progress.inventory):
                    return False  # Falha no requisito de evidência

            elif tipo == "clue":
                # O jogador precisa ter encontrado uma pista específica
                clue_id = requisito.get("related_clue_id")
                if clue_id and clue_id not in player_progress.discovered_clues:
                    return False  # Falha no requisito de pista

            elif tipo == "dialogue":
                # O jogador precisa ter falado com um NPC específico
                npc_name = requisito.get("npc_name")
                if npc_name and not self._verificar_conversa_com_npc(npc_name, player_progress):
                    return False  # Falha no requisito de diálogo

            elif tipo == "location":
                # O jogador precisa estar em um local específico
                localizacao_requerida = requisito.get("required_location_id")
                if player_progress.current_location_id != localizacao_requerida:
                    return False  # Falha no requisito de localização

        return True  # Se passou por todas as verificações, o objeto pode evoluir!


# Exemplo de uso similar ao anterior
if __name__ == "__main__":
    from data_loader import DataLoader
    from game_state import GameStateManager
    
    data_loader = DataLoader()
    game_state_manager = GameStateManager()
    
    data_loader.carregar_historia("estalagem_cervo_negro")
    
    player_progress = game_state_manager.create_session("detective", "estalagem_cervo_negro")
    
    qr_processor = QRCodeProcessor(data_loader, game_state_manager)
    
    result = qr_processor.processar_qr_code(
        player_progress.session_id, 
        "loc_main_hall"
    )
    
    print(json.dumps(result, indent=2))