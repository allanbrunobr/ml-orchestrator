"""
Sistema de logging estruturado para o ML Orchestrator.
Fornece logs em formato JSON para melhor observabilidade.
"""
import logging
import json
import time
import sys
from typing import Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime


class StructuredLogger:
    """Logger estruturado que gera logs em formato JSON"""
    
    def __init__(self, name: str = "ml_orchestrator"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Evita duplicação de handlers
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            
            # Formatter simples - o JSON será construído manualmente
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _create_log_entry(self, event: str, level: str = "INFO", **kwargs) -> Dict[str, Any]:
        """Cria uma entrada de log estruturada"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "event": event,
            "logger": self.logger.name
        }
        
        # Adiciona campos extras
        for key, value in kwargs.items():
            if value is not None:
                log_entry[key] = value
        
        return log_entry
    
    def info(self, event: str, **kwargs):
        """Log de nível INFO"""
        log_entry = self._create_log_entry(event, "INFO", **kwargs)
        self.logger.info(json.dumps(log_entry))
    
    def error(self, event: str, **kwargs):
        """Log de nível ERROR"""
        log_entry = self._create_log_entry(event, "ERROR", **kwargs)
        self.logger.error(json.dumps(log_entry))
    
    def warning(self, event: str, **kwargs):
        """Log de nível WARNING"""
        log_entry = self._create_log_entry(event, "WARNING", **kwargs)
        self.logger.warning(json.dumps(log_entry))
    
    def debug(self, event: str, **kwargs):
        """Log de nível DEBUG"""
        log_entry = self._create_log_entry(event, "DEBUG", **kwargs)
        self.logger.debug(json.dumps(log_entry))
    
    def log_execution_start(self, execution_id: str, flow_name: str, user_id: str, **kwargs):
        """Log especializado para início de execução"""
        self.info(
            "execution_start",
            execution_id=execution_id,
            flow_name=flow_name,
            user_id=user_id,
            **kwargs
        )
    
    def log_execution_end(self, execution_id: str, flow_name: str, duration: float, 
                         status: str = "success", **kwargs):
        """Log especializado para fim de execução"""
        self.info(
            "execution_end",
            execution_id=execution_id,
            flow_name=flow_name,
            duration_seconds=duration,
            status=status,
            **kwargs
        )
    
    def log_step_start(self, execution_id: str, step_name: str, 
                      params: Optional[Dict[str, Any]] = None, **kwargs):
        """Log especializado para início de step"""
        self.info(
            "step_start",
            execution_id=execution_id,
            step_name=step_name,
            params=params or {},
            **kwargs
        )
    
    def log_step_end(self, execution_id: str, step_name: str, duration: float,
                    status: str = "success", **kwargs):
        """Log especializado para fim de step"""
        level = "INFO" if status == "success" else "ERROR"
        event = "step_success" if status == "success" else "step_error"
        
        log_method = self.info if status == "success" else self.error
        log_method(
            event,
            execution_id=execution_id,
            step_name=step_name,
            duration_seconds=duration,
            status=status,
            **kwargs
        )
    
    def log_http_request(self, method: str, url: str, status_code: Optional[int] = None,
                        duration: Optional[float] = None, **kwargs):
        """Log especializado para requisições HTTP"""
        self.info(
            "http_request",
            method=method,
            url=url,
            status_code=status_code,
            duration_seconds=duration,
            **kwargs
        )
    
    @contextmanager
    def execution_context(self, execution_id: str, operation: str, **kwargs):
        """Context manager para medir duração e logar início/fim de operações"""
        start_time = time.time()
        
        # Log de início
        self.info(f"{operation}_start", execution_id=execution_id, **kwargs)
        
        try:
            yield
            # Log de sucesso
            duration = time.time() - start_time
            self.info(
                f"{operation}_success",
                execution_id=execution_id,
                duration_seconds=duration,
                **kwargs
            )
        except Exception as e:
            # Log de erro
            duration = time.time() - start_time
            self.error(
                f"{operation}_error",
                execution_id=execution_id,
                duration_seconds=duration,
                error=str(e),
                error_type=type(e).__name__,
                **kwargs
            )
            raise
    
    @contextmanager
    def step_context(self, execution_id: str, step_name: str, **kwargs):
        """Context manager específico para steps"""
        with self.execution_context(execution_id, f"step_{step_name}", step_name=step_name, **kwargs):
            yield


# Singleton global do logger
logger = StructuredLogger()


def get_logger(name: Optional[str] = None) -> StructuredLogger:
    """Factory function para obter uma instância do logger"""
    if name:
        return StructuredLogger(name)
    return logger