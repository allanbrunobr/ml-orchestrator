"""
Modelos de dados para o sistema de orquestração.
"""
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
from datetime import datetime
from config.settings import StepStatus


@dataclass
class StepResult:
    """Resultado da execução de um step individual"""
    step_name: str
    status: StepStatus
    duration: float
    started_at: datetime
    completed_at: datetime
    response: Optional[Any] = None
    error: Optional[str] = None
    error_details: Optional[str] = None
    url: Optional[str] = None
    status_code: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o resultado para dicionário"""
        return {
            "step_name": self.step_name,
            "status": self.status,
            "duration": self.duration,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "error": self.error,
            "url": self.url,
            "status_code": self.status_code
        }


@dataclass
class ExecutionContext:
    """Contexto de execução compartilhado entre steps"""
    execution_id: str
    user_id: str
    session_id: str
    flow_name: str
    request_data: Dict[str, Any]
    results: List[StepResult] = field(default_factory=list)
    
    def add_result(self, result: StepResult):
        """Adiciona um resultado ao contexto"""
        self.results.append(result)
    
    def get_successful_steps(self) -> List[str]:
        """Retorna lista de steps executados com sucesso"""
        return [r.step_name for r in self.results if r.status == StepStatus.SUCCESS]
    
    def has_critical_errors(self) -> bool:
        """Verifica se houve erros críticos"""
        return any(r.status == StepStatus.CRITICAL_ERROR for r in self.results)