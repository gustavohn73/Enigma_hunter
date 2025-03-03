import requests
import json
import os
from typing import Dict, List, Any, Optional, Tuple

class GerenciadorPersonagens:
    """
    Classe responsável por gerenciar a interação entre jogadores e personagens através da IA Ollama/llama3.
    """
    
    def __init__(self, modelo_ia: str = "llama3", url_ollama: str = "http://localhost:11434/api/generate"):
        """
        Inicializa o gerenciador de personagens.
        
        Args:
            modelo_ia: O modelo de IA a ser utilizado (padrão: llama3)
            url_ollama: URL da API do Ollama
        """
        self.modelo_ia = modelo_ia
        self.url_ollama = url_ollama
        self.historico_conversas: Dict[str, List[Dict[str, str]]] = {}  # jogador_id -> lista de mensagens
        self.personagens: Dict[str, Dict[str, Any]] = {}  # personagem_id -> dados do personagem
        
    def carregar_personagens(self, caminho_arquivo: str) -> None:
        """
        Carrega os dados dos personagens a partir de um arquivo JSON.
        
        Args:
            caminho_arquivo: Caminho para o arquivo JSON com os dados dos personagens
        """
        try:
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                self.personagens = json.load(f)
            print(f"Carregados {len(self.personagens)} personagens com sucesso.")
        except FileNotFoundError:
            print(f"Erro: Arquivo {caminho_arquivo} não encontrado.")
        except json.JSONDecodeError:
            print(f"Erro: Arquivo {caminho_arquivo} não é um JSON válido.")
        except Exception as e:
            print(f"Erro ao carregar personagens: {e}")
    
    def iniciar_conversa(self, jogador_id: str, personagem_id: str) -> str:
        """
        Inicia uma conversa entre jogador e personagem.
        
        Args:
            jogador_id: ID único do jogador
            personagem_id: ID do personagem com quem o jogador quer conversar
            
        Returns:
            Mensagem inicial do personagem
        """
        if personagem_id not in self.personagens:
            return "Erro: Personagem não encontrado."
        
        chave_conversa = f"{jogador_id}_{personagem_id}"
        
        # Inicializa o histórico se não existir
        if chave_conversa not in self.historico_conversas:
            self.historico_conversas[chave_conversa] = []
        
        personagem = self.personagens[personagem_id]
        estagio_atual = personagem.get("estagio_atual", 1)
        
        # Mensagem de introdução baseada no estágio atual do personagem
        mensagem_inicial = self._gerar_mensagem_inicial(personagem, estagio_atual)
        
        # Adiciona ao histórico
        self.historico_conversas[chave_conversa].append({
            "role": "assistant",
            "content": mensagem_inicial
        })
        
        return mensagem_inicial
    
    def _gerar_mensagem_inicial(self, personagem: Dict[str, Any], estagio: int) -> str:
        """
        Gera a mensagem inicial do personagem com base no seu estágio atual.
        
        Args:
            personagem: Dados do personagem
            estagio: Estágio atual do personagem
            
        Returns:
            Mensagem inicial formatada
        """
        # Busca a mensagem inicial correspondente ao estágio
        if f"mensagem_inicial_estagio_{estagio}" in personagem:
            return personagem[f"mensagem_inicial_estagio_{estagio}"]
        else:
            return personagem.get("mensagem_inicial", "Olá, como posso ajudar?")
    
    def processar_mensagem(self, jogador_id: str, personagem_id: str, mensagem: str) -> Dict[str, Any]:
        """
        Processa uma mensagem do jogador e retorna a resposta do personagem.
        
        Args:
            jogador_id: ID único do jogador
            personagem_id: ID do personagem
            mensagem: Conteúdo da mensagem do jogador
            
        Returns:
            Dicionário contendo a resposta e possíveis atualizações de estado
        """
        if personagem_id not in self.personagens:
            return {"resposta": "Erro: Personagem não encontrado.", "evolucao": False}
        
        chave_conversa = f"{jogador_id}_{personagem_id}"
        
        # Inicializa o histórico se não existir
        if chave_conversa not in self.historico_conversas:
            self.iniciar_conversa(jogador_id, personagem_id)
        
        # Adiciona mensagem do jogador ao histórico
        self.historico_conversas[chave_conversa].append({
            "role": "user",
            "content": mensagem
        })
        
        personagem = self.personagens[personagem_id]
        estagio_atual = personagem.get("estagio_atual", 1)
        
        # Gera o prompt baseado no contexto e estágio
        prompt = self._criar_prompt(personagem, estagio_atual, self.historico_conversas[chave_conversa])
        
        # Obtém resposta da IA
        resposta_ia = self._consultar_ia(prompt)
        
        # Verifica gatilhos para evolução
        evolucao, novo_estagio = self._verificar_evolucao(personagem, estagio_atual, mensagem, resposta_ia)
        
        # Adiciona resposta ao histórico
        self.historico_conversas[chave_conversa].append({
            "role": "assistant",
            "content": resposta_ia
        })
        
        # Limita o tamanho do histórico para evitar problemas de contexto muito grande
        if len(self.historico_conversas[chave_conversa]) > 20:
            # Mantém a primeira mensagem (contexto) e as últimas 19 mensagens
            self.historico_conversas[chave_conversa] = [
                self.historico_conversas[chave_conversa][0]
            ] + self.historico_conversas[chave_conversa][-19:]
        
        return {
            "resposta": resposta_ia,
            "evolucao": evolucao,
            "novo_estagio": novo_estagio if evolucao else estagio_atual,
            "pistas_reveladas": self._extrair_pistas(personagem, estagio_atual, mensagem, resposta_ia)
        }
    
    def _criar_prompt(self, personagem: Dict[str, Any], estagio: int, historico: List[Dict[str, str]]) -> str:
        """
        Cria o prompt a ser enviado para o modelo de IA.
        
        Args:
            personagem: Dados do personagem
            estagio: Estágio atual do personagem
            historico: Histórico da conversa
            
        Returns:
            Prompt formatado para a IA
        """
        # Informações do personagem no estágio atual
        contexto_personagem = personagem.get(f"contexto_estagio_{estagio}", personagem.get("contexto", ""))
        personalidade = personagem.get("personalidade", "")
        conhecimento = personagem.get(f"conhecimento_estagio_{estagio}", personagem.get("conhecimento", ""))
        restricoes = personagem.get(f"restricoes_estagio_{estagio}", personagem.get("restricoes", ""))
        
        # Formata o prompt
        prompt = f"""Você é {personagem.get('nome')}, {personagem.get('descricao', '')}.

CONTEXTO DO PERSONAGEM NO ESTÁGIO ATUAL ({estagio}):
{contexto_personagem}

PERSONALIDADE:
{personalidade}

CONHECIMENTO DISPONÍVEL NESTE ESTÁGIO:
{conhecimento}

RESTRIÇÕES:
{restricoes}

INSTRUÇÕES ESPECIAIS:
1. Mantenha-se fiel ao personagem e seu estágio atual de conhecimento.
2. Não revele informações além do que o personagem sabe no estágio atual.
3. Responda de forma natural e conversacional, mantendo o estilo de fala do personagem.
4. Suas respostas devem ter no máximo 3 parágrafos.

HISTÓRICO DA CONVERSA:
"""
        
        # Adiciona o histórico da conversa
        for msg in historico[-10:]:  # Limita ao contexto recente
            if msg["role"] == "user":
                prompt += f"\nJogador: {msg['content']}"
            else:
                prompt += f"\n{personagem.get('nome')}: {msg['content']}"
        
        # Finaliza o prompt
        prompt += f"\n\n{personagem.get('nome')}:"
        
        return prompt
    
    def _consultar_ia(self, prompt: str) -> str:
        """
        Envia o prompt para a API do Ollama e retorna a resposta.
        
        Args:
            prompt: Prompt formatado para o modelo
            
        Returns:
            Resposta gerada pela IA
        """
        try:
            payload = {
                "model": self.modelo_ia,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500
                }
            }
            
            response = requests.post(self.url_ollama, json=payload)
            
            if response.status_code == 200:
                resultado = response.json()
                return resultado.get("response", "Desculpe, não consegui processar sua solicitação.")
            else:
                print(f"Erro na API do Ollama: {response.status_code} - {response.text}")
                return "Desculpe, ocorreu um erro na comunicação com o personagem."
                
        except requests.RequestException as e:
            print(f"Erro ao consultar IA: {e}")
            return "Desculpe, ocorreu um erro na comunicação com o personagem."
    
    def _verificar_evolucao(self, personagem: Dict[str, Any], estagio_atual: int, 
                           mensagem_jogador: str, resposta_ia: str) -> Tuple[bool, int]:
        """
        Verifica se a conversa ativou algum gatilho de evolução do personagem.
        
        Args:
            personagem: Dados do personagem
            estagio_atual: Estágio atual do personagem
            mensagem_jogador: Mensagem enviada pelo jogador
            resposta_ia: Resposta gerada pela IA
            
        Returns:
            Tupla (evolução ocorreu, novo estágio)
        """
        # Verifica se existem gatilhos para o estágio atual
        gatilhos = personagem.get(f"gatilhos_evolucao_estagio_{estagio_atual}", [])
        
        if not gatilhos:
            return False, estagio_atual
        
        # Concatena mensagem e resposta para verificar os gatilhos
        texto_completo = f"{mensagem_jogador} {resposta_ia}".lower()
        
        for gatilho in gatilhos:
            palavras_chave = gatilho.get("palavras_chave", [])
            frases_chave = gatilho.get("frases_chave", [])
            combinacao_necessaria = gatilho.get("combinacao_necessaria", False)
            proximo_estagio = gatilho.get("proximo_estagio", estagio_atual + 1)
            
            # Verifica palavras-chave
            palavras_encontradas = all(palavra.lower() in texto_completo for palavra in palavras_chave) \
                                 if combinacao_necessaria else \
                                 any(palavra.lower() in texto_completo for palavra in palavras_chave)
            
            # Verifica frases-chave
            frases_encontradas = all(frase.lower() in texto_completo for frase in frases_chave) \
                               if combinacao_necessaria else \
                               any(frase.lower() in texto_completo for frase in frases_chave)
            
            # Se encontrou os gatilhos necessários, evolui o personagem
            if (not palavras_chave or palavras_encontradas) and (not frases_chave or frases_encontradas):
                # Atualiza o estágio do personagem
                self.personagens[personagem["id"]]["estagio_atual"] = proximo_estagio
                return True, proximo_estagio
        
        return False, estagio_atual
    
    def _extrair_pistas(self, personagem: Dict[str, Any], estagio: int,
                       mensagem_jogador: str, resposta_ia: str) -> List[Dict[str, str]]:
        """
        Extrai pistas a partir da conversa atual.
        
        Args:
            personagem: Dados do personagem
            estagio: Estágio atual do personagem
            mensagem_jogador: Mensagem enviada pelo jogador
            resposta_ia: Resposta gerada pela IA
            
        Returns:
            Lista de pistas encontradas na conversa
        """
        pistas_disponiveis = personagem.get(f"pistas_estagio_{estagio}", [])
        pistas_encontradas = []
        
        if not pistas_disponiveis:
            return []
        
        # Concatena mensagem e resposta para verificar pistas
        texto_completo = f"{mensagem_jogador} {resposta_ia}".lower()
        
        for pista in pistas_disponiveis:
            identificador = pista.get("id")
            gatilhos = pista.get("gatilhos", [])
            
            # Verifica se algum gatilho foi ativado
            for gatilho in gatilhos:
                if gatilho.lower() in texto_completo:
                    pistas_encontradas.append({
                        "id": identificador,
                        "titulo": pista.get("titulo"),
                        "descricao": pista.get("descricao")
                    })
                    break
        
        return pistas_encontradas
    
    def salvar_estado(self, caminho_arquivo: str) -> bool:
        """
        Salva o estado atual dos personagens em um arquivo JSON.
        
        Args:
            caminho_arquivo: Caminho para o arquivo de destino
            
        Returns:
            True se o salvamento foi bem-sucedido, False caso contrário
        """
        try:
            with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                json.dump(self.personagens, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            print(f"Erro ao salvar estado: {e}")
            return False
            
    def obter_informacoes_personagem(self, personagem_id: str, jogador_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtém informações sobre um personagem, considerando o estágio atual.
        
        Args:
            personagem_id: ID do personagem
            jogador_id: ID opcional do jogador para verificar o histórico
            
        Returns:
            Informações públicas do personagem no estágio atual
        """
        if personagem_id not in self.personagens:
            return {"erro": "Personagem não encontrado"}
        
        personagem = self.personagens[personagem_id]
        estagio_atual = personagem.get("estagio_atual", 1)
        
        # Filtra apenas as informações relevantes para o estágio atual
        info_publica = {
            "id": personagem.get("id"),
            "nome": personagem.get("nome"),
            "descricao": personagem.get("descricao"),
            "imagem": personagem.get(f"imagem_estagio_{estagio_atual}", personagem.get("imagem")),
            "localizacao": personagem.get(f"localizacao_estagio_{estagio_atual}", personagem.get("localizacao")),
            "estagio_atual": estagio_atual
        }
        
        # Adiciona o histórico de conversa se o jogador_id for fornecido
        if jogador_id:
            chave_conversa = f"{jogador_id}_{personagem_id}"
            if chave_conversa in self.historico_conversas:
                info_publica["historico"] = self.historico_conversas[chave_conversa]
        
        return info_publica
