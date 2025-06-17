"""
ML Orchestrator - FastAPI Application
Entry point para Cloud Run
"""
import os
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from handlers.orchestrator_handler import OrchestratorHandler
from utils.logger import get_logger
from config.settings import SERVER_CONFIG


# Configurar logger
logger = get_logger("main")

# Handler global para reutilização
orchestrator_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Inicializa recursos no startup e limpa no shutdown.
    """
    global orchestrator_handler
    
    # Startup
    logger.info("application_startup", port=SERVER_CONFIG["PORT"])
    orchestrator_handler = OrchestratorHandler()
    yield
    
    # Shutdown
    logger.info("application_shutdown")
    if orchestrator_handler:
        orchestrator_handler.shutdown()


# Criar aplicação FastAPI
app = FastAPI(
    title="ML Orchestrator",
    description="Sistema de orquestração para funções de Machine Learning",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS (ajustar conforme necessário)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar origens permitidas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Modelos Pydantic para validação
class OrchestrationRequest(BaseModel):
    """Modelo de requisição para orquestração"""
    user_id: str = Field(..., description="ID do usuário")
    session_id: str = Field(..., description="ID da sessão")
    create_user_embedding: bool = Field(default=False, description="Se deve criar embeddings do usuário")
    
    # Flags de controle de fluxo
    process_profession_orchestrator: bool = Field(default=True, description="Processar fluxo de profissão")
    process_vacancy_orchestrator: bool = Field(default=True, description="Processar fluxo de vaga")
    process_only_profession_course: bool = Field(default=False, description="Processar apenas curso de profissão")
    process_only_profession_skills: bool = Field(default=False, description="Processar apenas skills de profissão")
    process_only_vacancy_course: bool = Field(default=False, description="Processar apenas curso de vaga")
    process_only_vacancy_skills: bool = Field(default=False, description="Processar apenas skills de vaga")
    
    # Parâmetros opcionais
    identifier: str | None = Field(default=None, description="Identificador único da requisição")
    vacancy_id: str | None = Field(default=None, description="ID da vaga")
    vacancy_name: str | None = Field(default=None, description="Nome da vaga")
    vacancy_description: str | None = Field(default=None, description="Descrição da vaga")
    position_id: str | None = Field(default=None, description="ID da posição/profissão")
    position_name: str | None = Field(default=None, description="Nome da posição")
    career_name: str | None = Field(default=None, description="Nome da carreira")
    
    # Tokens de autenticação (opcionais)
    create_user_embeddings_token: str | None = None
    match_candidato_token: str | None = None
    match_analysis_user_vacancy_token: str | None = None
    gap_analysis_user_vacancy_token: str | None = None
    suggest_course_vacancy_token: str | None = None
    match_user_profession_token: str | None = None
    match_user_career_token: str | None = None
    match_analysis_user_profession_token: str | None = None
    gap_analysis_user_profession_token: str | None = None
    suggest_course_profession_token: str | None = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "session_id": "session456",
                "create_user_embedding": True,
                "process_profession_orchestrator": True,
                "process_vacancy_orchestrator": True
            }
        }


# Middleware para logging de requisições
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log todas as requisições HTTP"""
    start_time = time.time()
    
    # Log da requisição
    logger.info(
        "http_request_received",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None
    )
    
    # Processa requisição
    response = await call_next(request)
    
    # Log da resposta
    duration = time.time() - start_time
    logger.info(
        "http_request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration=duration
    )
    
    return response


@app.get("/", tags=["Info"])
async def root():
    """Endpoint raiz com informações da API"""
    return {
        "service": "ML Orchestrator",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "orchestrate": "/orchestrate",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint para Cloud Run.
    Verifica se o serviço está operacional.
    """
    try:
        # Verifica se o handler está inicializado
        if not orchestrator_handler:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready"
            )
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "ml-orchestrator"
        }
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


@app.post("/orchestrate", tags=["Orchestration"])
async def orchestrate(request: OrchestrationRequest):
    """
    Endpoint principal para orquestração de fluxos ML.
    
    Executa o fluxo apropriado baseado nos parâmetros fornecidos.
    """
    try:
        # Converte modelo Pydantic para dict
        request_data = request.model_dump(exclude_none=True)
        
        # Chama o handler
        response_data, status_code = orchestrator_handler.handle_request(request_data)
        
        # Se não for 200, retorna erro
        if status_code != 200:
            raise HTTPException(
                status_code=status_code,
                detail=response_data
            )
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "orchestration_error",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": str(e)}
        )


@app.post("/", tags=["Orchestration"])
async def orchestrate_root(request: Request):
    """
    Endpoint raiz POST para compatibilidade com Cloud Functions.
    Replica o comportamento do endpoint /orchestrate.
    """
    try:
        # Obtém o JSON da requisição
        request_data = await request.json()
        
        # Valida usando o modelo Pydantic
        orchestration_request = OrchestrationRequest(**request_data)
        
        # Chama o endpoint de orquestração
        return await orchestrate(orchestration_request)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid request", "message": str(e)}
        )
    except Exception as e:
        logger.error(
            "orchestration_root_error",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": str(e)}
        )


# Exception handler global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global para exceções não tratadas"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "path": request.url.path
        }
    )


if __name__ == "__main__":
    """Execução direta para desenvolvimento"""
    # Carrega variáveis de ambiente
    from dotenv import load_dotenv
    load_dotenv()
    
    # Configurações do servidor
    host = SERVER_CONFIG["HOST"]
    port = SERVER_CONFIG["PORT"]
    log_level = SERVER_CONFIG["LOG_LEVEL"].lower()
    
    logger.info(
        "starting_development_server",
        host=host,
        port=port,
        log_level=log_level
    )
    
    # Inicia servidor Uvicorn
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=True  # Hot reload em desenvolvimento
    )