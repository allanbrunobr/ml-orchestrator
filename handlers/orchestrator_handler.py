"""
Orchestrator Handler - Handler principal para requisições de orquestração.
"""
import uuid
import time
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

from core.flow_router import FlowRouter
from core.flow_executor import FlowExecutor
from core.models import ExecutionContext, StepResult
from config.settings import StepStatus
from utils.logger import get_logger
from utils.http_client import HttpClient


logger = get_logger("orchestrator_handler")


class OrchestratorHandler:
    """Handler principal para gerenciar requisições de orquestração"""
    
    def __init__(self):
        """Inicializa o handler com suas dependências"""
        self.flow_router = FlowRouter()
        self.flow_executor = FlowExecutor()
        self.logger = logger
        
        # Cliente HTTP para webhook final (se configurado)
        self.webhook_client = HttpClient(default_timeout=15)
        
        # Tracking de requisições para evitar duplicatas
        self.execution_tracker = {}
        self.execution_tracker_ttl = 300  # 5 minutos
    
    def handle_request(self, request_data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """
        Handler principal para requisições de orquestração.
        
        Args:
            request_data: Dados da requisição
            
        Returns:
            Tupla (response_dict, status_code)
        """
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        self.logger.info(
            "request_received",
            execution_id=execution_id,
            request_keys=list(request_data.keys())
        )
        
        try:
            # Validação básica da requisição
            validation_errors = self._validate_request(request_data)
            if validation_errors:
                self.logger.warning(
                    "request_validation_failed",
                    execution_id=execution_id,
                    errors=validation_errors
                )
                return {"errors": validation_errors}, 400
            
            # Extrai informações básicas
            user_id = request_data["user_id"]
            session_id = request_data["session_id"]
            
            # Verifica duplicatas
            if self._is_duplicate_request(user_id, session_id, request_data):
                self.logger.warning(
                    "duplicate_request_detected",
                    execution_id=execution_id,
                    user_id=user_id,
                    session_id=session_id
                )
            
            # Determina qual fluxo executar
            flow_name = self.flow_router.determine_flow(request_data)
            flow_definition = self.flow_router.get_flow_definition(flow_name)
            
            # Valida parâmetros do fluxo
            flow_errors = self.flow_router.validate_flow_params(flow_name, request_data)
            if flow_errors:
                return {"errors": flow_errors, "flow": flow_name}, 400
            
            self.logger.log_execution_start(execution_id, flow_name, user_id)
            
            # Filtra steps baseado no contexto
            steps = self.flow_router.filter_steps_by_context(flow_definition, request_data)
            
            if not steps:
                self.logger.warning(
                    "no_steps_to_execute",
                    execution_id=execution_id,
                    flow_name=flow_name
                )
                return {
                    "execution_id": execution_id,
                    "flow_name": flow_name,
                    "message": "No steps to execute after filtering"
                }, 200
            
            # Cria contexto de execução
            context = ExecutionContext(
                execution_id=execution_id,
                user_id=user_id,
                session_id=session_id,
                flow_name=flow_name,
                request_data=request_data
            )
            
            # Executa o fluxo
            results = self.flow_executor.execute_flow(steps, context)
            
            # Monta resposta
            duration = time.time() - start_time
            response = self._build_response(context, results, duration)
            
            # Executa webhook se configurado
            self._execute_webhook(response)
            
            # Log de finalização
            self.logger.log_execution_end(
                execution_id=execution_id,
                flow_name=flow_name,
                duration=duration,
                status="completed",
                total_steps=len(results),
                successful_steps=len([r for r in results if r.status == StepStatus.SUCCESS])
            )
            
            return response, 200
            
        except Exception as e:
            # Tratamento de erros não esperados
            duration = time.time() - start_time
            self.logger.error(
                "handler_exception",
                execution_id=execution_id,
                error=str(e),
                error_type=type(e).__name__,
                duration=duration
            )
            
            return {
                "execution_id": execution_id,
                "error": "Internal server error",
                "message": str(e),
                "duration": duration
            }, 500
    
    def _validate_request(self, request_data: Dict[str, Any]) -> list[str]:
        """
        Valida dados básicos da requisição.
        
        Args:
            request_data: Dados da requisição
            
        Returns:
            Lista de erros de validação
        """
        errors = []
        
        # Campos obrigatórios
        if not request_data.get("user_id"):
            errors.append("Missing required field: user_id")
        elif not isinstance(request_data["user_id"], str):
            errors.append("Field 'user_id' must be a string")
        
        if not request_data.get("session_id"):
            errors.append("Missing required field: session_id")
        elif not isinstance(request_data["session_id"], str):
            errors.append("Field 'session_id' must be a string")
        
        # Validação de tipos para flags booleanas
        boolean_fields = [
            "create_user_embedding",
            "process_profession_orchestrator",
            "process_vacancy_orchestrator",
            "process_only_profession_course",
            "process_only_profession_skills",
            "process_only_vacancy_course",
            "process_only_vacancy_skills"
        ]
        
        for field in boolean_fields:
            if field in request_data and not isinstance(request_data[field], bool):
                errors.append(f"Field '{field}' must be a boolean")
        
        # Validação de tokens (se fornecidos, devem ser strings)
        token_fields = [
            "create_user_embeddings_token",
            "match_candidato_token",
            "match_analysis_user_vacancy_token",
            "gap_analysis_user_vacancy_token",
            "suggest_course_vacancy_token",
            "match_user_profession_token",
            "match_user_career_token",
            "match_analysis_user_profession_token",
            "gap_analysis_user_profession_token",
            "suggest_course_profession_token"
        ]
        
        for field in token_fields:
            if field in request_data and request_data[field] is not None:
                if not isinstance(request_data[field], str):
                    errors.append(f"Field '{field}' must be a string if provided")
        
        return errors
    
    def _is_duplicate_request(self, 
                            user_id: str, 
                            session_id: str, 
                            request_data: Dict[str, Any]) -> bool:
        """
        Verifica se é uma requisição duplicada recente.
        
        Args:
            user_id: ID do usuário
            session_id: ID da sessão
            request_data: Dados da requisição
            
        Returns:
            True se for duplicata
        """
        # Cria chave única para a requisição
        identifier = request_data.get("identifier", "")
        request_key = f"{user_id}_{session_id}_{identifier}"
        
        current_time = time.time()
        
        # Limpa entradas antigas
        self._cleanup_execution_tracker()
        
        # Verifica se já foi processada recentemente
        if request_key in self.execution_tracker:
            last_execution = self.execution_tracker[request_key]
            time_diff = current_time - last_execution
            
            if time_diff < self.execution_tracker_ttl:
                return True
        
        # Registra nova execução
        self.execution_tracker[request_key] = current_time
        return False
    
    def _cleanup_execution_tracker(self):
        """Remove entradas antigas do tracker de execução"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.execution_tracker.items()
            if current_time - timestamp > self.execution_tracker_ttl
        ]
        
        for key in expired_keys:
            del self.execution_tracker[key]
    
    def _build_response(self, 
                       context: ExecutionContext, 
                       results: list[StepResult],
                       duration: float) -> Dict[str, Any]:
        """
        Constrói a resposta final da requisição.
        
        Args:
            context: Contexto de execução
            results: Resultados dos steps
            duration: Duração total
            
        Returns:
            Dicionário de resposta
        """
        # Informações básicas
        response = {
            "execution_id": context.execution_id,
            "flow_name": context.flow_name,
            "user_id": context.user_id,
            "session_id": context.session_id,
            "duration": duration,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Adiciona campos opcionais se presentes
        optional_fields = ["identifier", "vacancy_id", "vacancy_name", 
                          "position_id", "career_name"]
        for field in optional_fields:
            if field in context.request_data and context.request_data[field]:
                response[field] = context.request_data[field]
        
        # Resumo dos resultados
        response["summary"] = {
            "total_steps": len(results),
            "successful": len([r for r in results if r.status == StepStatus.SUCCESS]),
            "failed": len([r for r in results if r.status == StepStatus.FAILED]),
            "skipped": len([r for r in results if r.status == StepStatus.SKIPPED]),
            "critical_errors": len([r for r in results if r.status == StepStatus.CRITICAL_ERROR])
        }
        
        # Detalhes dos steps
        response["steps"] = [
            {
                "step_name": r.step_name,
                "status": r.status,
                "duration": r.duration,
                "started_at": r.started_at.isoformat() + "Z",
                "completed_at": r.completed_at.isoformat() + "Z",
                "error": r.error,
                "status_code": r.status_code
            }
            for r in results
        ]
        
        # Adiciona flag de erro se houve falhas críticas
        if any(r.status == StepStatus.CRITICAL_ERROR for r in results):
            response["has_critical_errors"] = True
        
        return response
    
    def _execute_webhook(self, response: Dict[str, Any]):
        """
        Executa webhook final se configurado.
        
        Args:
            response: Resposta a enviar no webhook
        """
        import os
        webhook_url = os.getenv("DEFAULT_WEBHOOK_URL")
        
        if not webhook_url:
            self.logger.debug("webhook_skipped", reason="no_url_configured")
            return
        
        try:
            self.logger.info(
                "webhook_execution_start",
                execution_id=response.get("execution_id"),
                url=webhook_url
            )
            
            webhook_response = self.webhook_client.post(
                url=webhook_url,
                json_payload=response
            )
            
            if webhook_response.is_success:
                self.logger.info(
                    "webhook_success",
                    execution_id=response.get("execution_id"),
                    status_code=webhook_response.status_code
                )
            else:
                self.logger.warning(
                    "webhook_failed",
                    execution_id=response.get("execution_id"),
                    status_code=webhook_response.status_code,
                    error=webhook_response.error
                )
                
        except Exception as e:
            self.logger.error(
                "webhook_exception",
                execution_id=response.get("execution_id"),
                error=str(e)
            )
    
    def shutdown(self):
        """Libera recursos do handler"""
        self.webhook_client.close()
        if hasattr(self.flow_executor, 'step_executor'):
            self.flow_executor.step_executor.close()