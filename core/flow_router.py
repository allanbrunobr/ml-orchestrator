"""
Flow Router - Responsável por determinar qual fluxo executar e filtrar steps.
"""
from typing import Dict, Any, List, Optional
from config.settings import FlowConfig, FlowDefinition, FlowName, FlowStep
from utils.logger import get_logger


logger = get_logger("flow_router")


class FlowRouter:
    """Roteador de fluxos baseado em parâmetros da requisição"""
    
    def __init__(self):
        self.flows = FlowConfig.FLOWS
        self.logger = logger
    
    def determine_flow(self, request_data: Dict[str, Any]) -> str:
        """
        Determina qual fluxo executar baseado nos parâmetros da requisição.
        
        Args:
            request_data: Dados da requisição
            
        Returns:
            Nome do fluxo a ser executado
        """
        # Log dos parâmetros de decisão
        self.logger.debug(
            "flow_determination",
            process_only_profession_course=request_data.get('process_only_profession_course', False),
            process_only_profession_skills=request_data.get('process_only_profession_skills', False),
            process_only_vacancy_course=request_data.get('process_only_vacancy_course', False),
            process_only_vacancy_skills=request_data.get('process_only_vacancy_skills', False),
            create_user_embedding=request_data.get('create_user_embedding', False)
        )
        
        # Fluxos específicos de profissão
        if request_data.get('process_only_profession_course'):
            flow_name = FlowName.COURSE_TO_PROFESSION
            self.logger.info("flow_selected", flow_name=flow_name, reason="process_only_profession_course=True")
            return flow_name
        
        if request_data.get('process_only_profession_skills'):
            flow_name = FlowName.ANALYSIS_TO_PROFESSION
            self.logger.info("flow_selected", flow_name=flow_name, reason="process_only_profession_skills=True")
            return flow_name
        
        # Fluxos específicos de vaga
        if request_data.get('process_only_vacancy_course'):
            flow_name = FlowName.COURSE_TO_VACANCY
            self.logger.info("flow_selected", flow_name=flow_name, reason="process_only_vacancy_course=True")
            return flow_name
        
        if request_data.get('process_only_vacancy_skills'):
            flow_name = FlowName.ANALYSIS_TO_VACANCY
            self.logger.info("flow_selected", flow_name=flow_name, reason="process_only_vacancy_skills=True")
            return flow_name
        
        # Fluxos padrão
        if request_data.get('create_user_embedding', False):
            flow_name = FlowName.UPDATE_PROFILE
            self.logger.info("flow_selected", flow_name=flow_name, reason="create_user_embedding=True")
            return flow_name
        
        # Fluxo padrão quando nenhuma flag específica está ativa
        flow_name = FlowName.FIRST_LOGIN
        self.logger.info("flow_selected", flow_name=flow_name, reason="default_flow")
        return flow_name
    
    def get_flow_definition(self, flow_name: str) -> FlowDefinition:
        """
        Retorna a definição completa de um fluxo.
        
        Args:
            flow_name: Nome do fluxo
            
        Returns:
            FlowDefinition do fluxo solicitado
            
        Raises:
            ValueError: Se o fluxo não existir
        """
        flow_def = self.flows.get(flow_name)
        
        if not flow_def:
            self.logger.error("unknown_flow", flow_name=flow_name)
            raise ValueError(f"Unknown flow: {flow_name}")
        
        self.logger.debug(
            "flow_definition_retrieved",
            flow_name=flow_name,
            step_count=len(flow_def.steps),
            requires_embeddings=flow_def.requires_embeddings
        )
        
        return flow_def
    
    def filter_steps_by_context(self, 
                               flow_def: FlowDefinition, 
                               request_data: Dict[str, Any]) -> List[FlowStep]:
        """
        Filtra os steps baseado no contexto da requisição.
        Remove steps de vaga ou profissão conforme as flags.
        
        Args:
            flow_def: Definição do fluxo
            request_data: Dados da requisição
            
        Returns:
            Lista filtrada de steps
        """
        process_vacancy = request_data.get('process_vacancy_orchestrator', True)
        process_profession = request_data.get('process_profession_orchestrator', True)
        
        # Se ambas as flags são True, retorna todos os steps
        if process_vacancy and process_profession:
            self.logger.debug(
                "steps_filter",
                action="no_filter",
                original_count=len(flow_def.steps),
                filtered_count=len(flow_def.steps)
            )
            return flow_def.steps
        
        filtered_steps = []
        
        for step in flow_def.steps:
            # Se é um step de vaga e não devemos processar vagas
            if 'vacancy' in step.name and not process_vacancy:
                self.logger.debug("step_filtered_out", step_name=step.name, reason="vacancy_disabled")
                continue
            
            # Se é um step de profissão e não devemos processar profissões
            if ('profession' in step.name or 'carreira' in step.name) and not process_profession:
                self.logger.debug("step_filtered_out", step_name=step.name, reason="profession_disabled")
                continue
            
            # Step não é específico ou deve ser incluído
            filtered_steps.append(step)
        
        self.logger.info(
            "steps_filtered",
            original_count=len(flow_def.steps),
            filtered_count=len(filtered_steps),
            process_vacancy=process_vacancy,
            process_profession=process_profession
        )
        
        return filtered_steps
    
    def should_skip_step(self, 
                        step: FlowStep, 
                        request_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Verifica se um step específico deve ser pulado baseado em condições.
        
        Args:
            step: Step a verificar
            request_data: Dados da requisição
            
        Returns:
            Tupla (should_skip, reason)
        """
        # Pula match_usuario_profissao se position_id foi fornecido
        if step.name == 'match_usuario_profissao' and request_data.get('position_id'):
            return True, "position_id provided"
        
        # Pula match_candidato se vacancy_id foi fornecido
        if step.name == 'match_candidato' and request_data.get('vacancy_id'):
            return True, "vacancy_id provided"
        
        # Pula match_usuario_carreira se position_id E career_name foram fornecidos
        if step.name == 'match_usuario_carreira':
            if request_data.get('position_id') and request_data.get('career_name'):
                return True, "both position_id and career_name provided"
        
        return False, None
    
    def validate_flow_params(self, 
                           flow_name: str, 
                           request_data: Dict[str, Any]) -> List[str]:
        """
        Valida se todos os parâmetros necessários para o fluxo estão presentes.
        
        Args:
            flow_name: Nome do fluxo
            request_data: Dados da requisição
            
        Returns:
            Lista de erros de validação (vazia se tudo OK)
        """
        errors = []
        
        # Parâmetros obrigatórios para todos os fluxos
        if not request_data.get('user_id'):
            errors.append("Missing required parameter: user_id")
        
        if not request_data.get('session_id'):
            errors.append("Missing required parameter: session_id")
        
        # Validações específicas por fluxo
        flow_def = self.flows.get(flow_name)
        if flow_def:
            # Se requer embeddings, precisa do session_id válido
            if flow_def.requires_embeddings and not request_data.get('session_id'):
                errors.append("Flow requires embeddings but session_id is missing")
        
        if errors:
            self.logger.warning(
                "flow_validation_failed",
                flow_name=flow_name,
                errors=errors
            )
        
        return errors