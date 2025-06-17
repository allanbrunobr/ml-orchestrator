"""
Configurações centralizadas para o ML Orchestrator.
Define todos os fluxos, steps e suas dependências.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class FlowName(str, Enum):
    """Nomes dos fluxos disponíveis"""
    UPDATE_PROFILE = "update_profile"
    FIRST_LOGIN = "first_login"
    COURSE_TO_PROFESSION = "course_to_profession"
    ANALYSIS_TO_PROFESSION = "analysis_to_profession"
    COURSE_TO_VACANCY = "course_to_vacancy"
    ANALYSIS_TO_VACANCY = "analysis_to_vacancy"


class StepStatus(str, Enum):
    """Status possíveis de um step"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CRITICAL_ERROR = "critical_error"


@dataclass
class FlowStep:
    """Define um step individual em um fluxo"""
    name: str
    function_name: str
    url_env_var: str
    timeout: int = 120
    required_params: List[str] = field(default_factory=list)
    parallel_group: Optional[str] = None
    
    def get_url(self) -> Optional[str]:
        """Obtém a URL do ambiente"""
        return os.getenv(self.url_env_var)


@dataclass
class FlowDefinition:
    """Define um fluxo completo"""
    name: str
    steps: List[FlowStep]
    requires_embeddings: bool = False
    description: str = ""


class FlowConfig:
    """Configuração centralizada de todos os fluxos"""
    
    # Definição de todos os steps disponíveis
    STEPS = {
        'create_embeddings': FlowStep(
            name='create_embeddings',
            function_name='_call_create_user_embeddings',
            url_env_var='DEFAULT_CREATE_USER_EMBEDDINGS_URL',
            timeout=300,
            required_params=['session_id']
        ),
        
        # Steps de Vaga
        'match_candidato': FlowStep(
            name='match_candidato',
            function_name='_call_match_candidato',
            url_env_var='DEFAULT_MATCH_CANDIDATO_URL',
            required_params=['user_id']
        ),
        'match_analysis_user_vacancy': FlowStep(
            name='match_analysis_user_vacancy',
            function_name='_call_match_analysis_user_vacancy',
            url_env_var='DEFAULT_MATCH_ANALYSIS_USER_VACANCY_URL',
            parallel_group='vacancy_parallel',
            required_params=['user_id']
        ),
        'gap_analysis_user_vacancy': FlowStep(
            name='gap_analysis_user_vacancy',
            function_name='_call_gap_analysis_user_vacancy',
            url_env_var='DEFAULT_GAP_ANALYSIS_USER_VACANCY_URL',
            required_params=['user_id']
        ),
        'suggest_course_vacancy': FlowStep(
            name='suggest_course_vacancy',
            function_name='_call_suggest_course_vacancy',
            url_env_var='DEFAULT_SUGGEST_COURSE_VACANCY_URL',
            parallel_group='vacancy_parallel',
            required_params=['user_id']
        ),
        
        # Steps de Profissão
        'match_usuario_profissao': FlowStep(
            name='match_usuario_profissao',
            function_name='_call_match_usuario_profissao',
            url_env_var='MATCH_USUARIO_PROFISSAO_URL',
            required_params=['user_id']
        ),
        'match_usuario_carreira': FlowStep(
            name='match_usuario_carreira',
            function_name='_call_match_usuario_carreira',
            url_env_var='MATCH_USUARIO_CARREIRA_URL',
            parallel_group='profession_parallel',
            required_params=['user_id']
        ),
        'match_analysis_user_profession': FlowStep(
            name='match_analysis_user_profession',
            function_name='_call_match_analysis_user_profession',
            url_env_var='MATCH_ANALYSIS_USER_PROFESSION_URL',
            parallel_group='profession_parallel',
            required_params=['user_id']
        ),
        'gap_analysis_user_profession': FlowStep(
            name='gap_analysis_user_profession',
            function_name='_call_gap_analysis_user_profession',
            url_env_var='GAP_ANALYSIS_USER_PROFESSION_URL',
            required_params=['user_id']
        ),
        'suggest_course_profession': FlowStep(
            name='suggest_course_profession',
            function_name='_call_suggest_course_profession',
            url_env_var='SUGGEST_COURSE_PROFESSION_URL',
            required_params=['user_id']
        )
    }
    
    # Definição de todos os fluxos
    FLOWS = {
        FlowName.UPDATE_PROFILE: FlowDefinition(
            name=FlowName.UPDATE_PROFILE,
            requires_embeddings=True,
            description="Fluxo completo com criação de embeddings",
            steps=[
                STEPS['create_embeddings'],
                STEPS['match_usuario_profissao'],
                STEPS['match_candidato'],
                STEPS['match_usuario_carreira'],
                STEPS['match_analysis_user_profession'],
                STEPS['gap_analysis_user_profession'],
                STEPS['suggest_course_profession'],
                STEPS['match_analysis_user_vacancy'],
                STEPS['gap_analysis_user_vacancy'],
                STEPS['suggest_course_vacancy']
            ]
        ),
        
        FlowName.FIRST_LOGIN: FlowDefinition(
            name=FlowName.FIRST_LOGIN,
            requires_embeddings=False,
            description="Fluxo inicial sem criação de embeddings",
            steps=[
                STEPS['match_usuario_profissao'],
                STEPS['match_candidato'],
                STEPS['match_usuario_carreira'],
                STEPS['match_analysis_user_profession'],
                STEPS['gap_analysis_user_profession'],
                STEPS['suggest_course_profession'],
                STEPS['match_analysis_user_vacancy'],
                STEPS['gap_analysis_user_vacancy'],
                STEPS['suggest_course_vacancy']
            ]
        ),
        
        FlowName.COURSE_TO_PROFESSION: FlowDefinition(
            name=FlowName.COURSE_TO_PROFESSION,
            requires_embeddings=False,
            description="Apenas sugestão de cursos para profissão",
            steps=[STEPS['suggest_course_profession']]
        ),
        
        FlowName.ANALYSIS_TO_PROFESSION: FlowDefinition(
            name=FlowName.ANALYSIS_TO_PROFESSION,
            requires_embeddings=False,
            description="Análise de skills para profissão",
            steps=[
                STEPS['match_analysis_user_profession'],
                STEPS['gap_analysis_user_profession']
            ]
        ),
        
        FlowName.COURSE_TO_VACANCY: FlowDefinition(
            name=FlowName.COURSE_TO_VACANCY,
            requires_embeddings=False,
            description="Apenas sugestão de cursos para vaga",
            steps=[STEPS['suggest_course_vacancy']]
        ),
        
        FlowName.ANALYSIS_TO_VACANCY: FlowDefinition(
            name=FlowName.ANALYSIS_TO_VACANCY,
            requires_embeddings=False,
            description="Análise de skills para vaga",
            steps=[
                STEPS['match_analysis_user_vacancy'],
                STEPS['gap_analysis_user_vacancy']
            ]
        )
    }
    
    @classmethod
    def get_flow(cls, flow_name: str) -> Optional[FlowDefinition]:
        """Retorna a definição de um fluxo específico"""
        return cls.FLOWS.get(flow_name)
    
    @classmethod
    def get_step(cls, step_name: str) -> Optional[FlowStep]:
        """Retorna a definição de um step específico"""
        return cls.STEPS.get(step_name)


# Configurações do servidor
SERVER_CONFIG = {
    "HOST": os.getenv("HOST", "0.0.0.0"),
    "PORT": int(os.getenv("PORT", "8080")),
    "WORKERS": int(os.getenv("WORKERS", "4")),
    "TIMEOUT": int(os.getenv("TIMEOUT", "540")),
    "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO")
}

# Configurações de logging
LOGGING_CONFIG = {
    "VERSION": 1,
    "DISABLE_EXISTING_LOGGERS": False,
    "FORMATTERS": {
        "default": {
            "FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "HANDLERS": {
        "default": {
            "CLASS": "logging.StreamHandler",
            "LEVEL": SERVER_CONFIG["LOG_LEVEL"],
            "FORMATTER": "json" if os.getenv("LOG_FORMAT") == "json" else "default",
            "STREAM": "ext://sys.stdout"
        }
    },
    "LOGGERS": {
        "ml_orchestrator": {
            "LEVEL": SERVER_CONFIG["LOG_LEVEL"],
            "HANDLERS": ["default"],
            "PROPAGATE": False
        }
    }
}