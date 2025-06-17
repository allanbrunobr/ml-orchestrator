"""
Step Executor - Responsável por executar steps individuais.
"""
import time
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

from config.settings import FlowStep, StepStatus
from core.models import StepResult, ExecutionContext
from core.flow_router import FlowRouter
from utils.http_client import HttpClient, HttpResponse
from utils.logger import get_logger


logger = get_logger("step_executor")


class StepExecutor:
    """Executor de steps individuais"""
    
    def __init__(self):
        """Inicializa o executor de steps"""
        self.http_client = HttpClient(
            default_timeout=120,
            default_headers={
                'Content-Type': 'application/json',
                'X-Orchestrator': 'senai-ml-orchestrator'
            }
        )
        self.flow_router = FlowRouter()
        self.logger = logger
    
    def execute_step(self, 
                    step: FlowStep, 
                    context: ExecutionContext) -> StepResult:
        """
        Executa um step individual.
        
        Args:
            step: Step a executar
            context: Contexto de execução
            
        Returns:
            Resultado da execução
        """
        start_time = time.time()
        started_at = datetime.utcnow()
        
        self.logger.info(
            "step_execution_start",
            execution_id=context.execution_id,
            step_name=step.name,
            user_id=context.user_id
        )
        
        try:
            # Verifica se o step deve ser pulado
            should_skip, skip_reason = self.flow_router.should_skip_step(step, context.request_data)
            if should_skip:
                self.logger.info(
                    "step_skipped",
                    execution_id=context.execution_id,
                    step_name=step.name,
                    reason=skip_reason
                )
                
                return StepResult(
                    step_name=step.name,
                    status=StepStatus.SKIPPED,
                    duration=time.time() - start_time,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    error=f"Skipped: {skip_reason}"
                )
            
            # Obtém URL do step
            url = step.get_url()
            if not url:
                self.logger.warning(
                    "step_url_not_configured",
                    execution_id=context.execution_id,
                    step_name=step.name,
                    env_var=step.url_env_var
                )
                
                return StepResult(
                    step_name=step.name,
                    status=StepStatus.SKIPPED,
                    duration=time.time() - start_time,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    error=f"URL not configured: {step.url_env_var}"
                )
            
            # Prepara payload e headers
            payload = self._prepare_payload(step, context)
            headers = self._prepare_headers(step, context)
            
            # Log do payload (sem dados sensíveis)
            self.logger.debug(
                "step_request_prepared",
                execution_id=context.execution_id,
                step_name=step.name,
                url=url,
                payload_keys=list(payload.keys()),
                has_auth=bool(headers.get('Authorization'))
            )
            
            # Faz a requisição HTTP
            with self.logger.step_context(context.execution_id, step.name):
                response = self.http_client.post(
                    url=url,
                    json_payload=payload,
                    headers=headers,
                    timeout=step.timeout
                )
            
            duration = time.time() - start_time
            
            # Processa resposta
            if response.is_success:
                status = StepStatus.SUCCESS
                error = None
            else:
                status = StepStatus.FAILED
                error = response.error or f"HTTP {response.status_code}"
            
            result = StepResult(
                step_name=step.name,
                status=status,
                duration=duration,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                response=response.body,
                error=error,
                url=url,
                status_code=response.status_code
            )
            
            self.logger.info(
                "step_execution_end",
                execution_id=context.execution_id,
                step_name=step.name,
                status=status,
                duration=duration,
                status_code=response.status_code
            )
            
            return result
            
        except Exception as e:
            # Captura exceções não tratadas
            duration = time.time() - start_time
            error_msg = str(e)
            error_details = traceback.format_exc()
            
            self.logger.error(
                "step_execution_exception",
                execution_id=context.execution_id,
                step_name=step.name,
                error=error_msg,
                traceback=error_details,
                duration=duration
            )
            
            return StepResult(
                step_name=step.name,
                status=StepStatus.CRITICAL_ERROR,
                duration=duration,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error=error_msg,
                error_details=error_details
            )
    
    def _prepare_payload(self, 
                        step: FlowStep, 
                        context: ExecutionContext) -> Dict[str, Any]:
        """
        Prepara o payload para o step baseado em suas necessidades.
        
        Args:
            step: Step sendo executado
            context: Contexto de execução
            
        Returns:
            Payload preparado
        """
        request_data = context.request_data
        
        # Payload base para maioria dos steps
        payload = {"user_id": context.user_id}
        
        # Payload especial para create_embeddings
        if step.name == "create_embeddings":
            return {"sessionId": context.session_id}
        
        # Adiciona parâmetros específicos de vaga
        if "vacancy" in step.name:
            vacancy_params = {
                "vacancy_id": request_data.get("vacancy_id"),
                "vacancy_name": request_data.get("vacancy_name"),
                "vacancy_description": request_data.get("vacancy_description")
            }
            # Adiciona apenas parâmetros não nulos
            payload.update({k: v for k, v in vacancy_params.items() if v is not None})
        
        # Adiciona parâmetros específicos de profissão
        if "profession" in step.name or "carreira" in step.name:
            profession_params = {
                "position_id": request_data.get("position_id"),
                "career_name": request_data.get("career_name"),
                "position_name": request_data.get("position_name")
            }
            # Adiciona apenas parâmetros não nulos
            payload.update({k: v for k, v in profession_params.items() if v is not None})
        
        self.logger.debug(
            "payload_prepared",
            step_name=step.name,
            payload_keys=list(payload.keys())
        )
        
        return payload
    
    def _prepare_headers(self, 
                        step: FlowStep, 
                        context: ExecutionContext) -> Dict[str, str]:
        """
        Prepara os headers para o step.
        
        Args:
            step: Step sendo executado
            context: Contexto de execução
            
        Returns:
            Headers preparados
        """
        # Headers padrão já estão no http_client
        headers = {}
        
        # Adiciona token de autorização se disponível
        # Procura por token específico do step
        token_key = f"{step.name}_token"
        token = context.request_data.get(token_key)
        
        # Se não encontrou token específico, tenta tokens genéricos
        if not token:
            if "vacancy" in step.name:
                # Tenta tokens de vaga genéricos
                for key in ["match_candidato_token", "match_analysis_user_vacancy_token", 
                           "gap_analysis_user_vacancy_token", "suggest_course_vacancy_token"]:
                    if key in context.request_data:
                        token = context.request_data.get(key)
                        break
            elif "profession" in step.name or "carreira" in step.name:
                # Tenta tokens de profissão genéricos
                for key in ["match_user_profession_token", "match_user_career_token",
                           "match_analysis_user_profession_token", "gap_analysis_user_profession_token",
                           "suggest_course_profession_token"]:
                    if key in context.request_data:
                        token = context.request_data.get(key)
                        break
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
            self.logger.debug(
                "auth_token_added",
                step_name=step.name,
                token_source=token_key if context.request_data.get(token_key) else "generic"
            )
        
        return headers
    
    def close(self):
        """Fecha recursos do executor"""
        self.http_client.close()