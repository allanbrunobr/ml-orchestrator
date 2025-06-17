"""
Cliente HTTP reutilizável com tratamento de erros e logging estruturado.
"""
import requests
import json
import time
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger


logger = get_logger("http_client")


class HttpMethod(str, Enum):
    """Métodos HTTP suportados"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class HttpResponse:
    """Resposta estruturada de uma requisição HTTP"""
    status_code: int
    body: Any
    status: str
    url: str
    method: str
    duration: float
    error: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    
    @property
    def is_success(self) -> bool:
        """Verifica se a requisição foi bem sucedida"""
        return 200 <= self.status_code < 300
    
    @property
    def is_client_error(self) -> bool:
        """Verifica se houve erro do cliente (4xx)"""
        return 400 <= self.status_code < 500
    
    @property
    def is_server_error(self) -> bool:
        """Verifica se houve erro do servidor (5xx)"""
        return 500 <= self.status_code < 600


class HttpClient:
    """Cliente HTTP com funcionalidades avançadas"""
    
    def __init__(self, 
                 default_timeout: int = 120,
                 default_headers: Optional[Dict[str, str]] = None,
                 retry_count: int = 0,
                 retry_delay: float = 1.0):
        """
        Inicializa o cliente HTTP.
        
        Args:
            default_timeout: Timeout padrão em segundos
            default_headers: Headers padrão para todas as requisições
            retry_count: Número de tentativas em caso de erro
            retry_delay: Delay entre tentativas em segundos
        """
        self.default_timeout = default_timeout
        self.default_headers = default_headers or {}
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.session = requests.Session()
        
        # Configura headers padrão na sessão
        self.session.headers.update(self.default_headers)
    
    def _parse_response_body(self, response: requests.Response) -> Any:
        """Tenta parsear o corpo da resposta"""
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text
    
    def _execute_request(self, 
                        method: Union[str, HttpMethod],
                        url: str,
                        headers: Optional[Dict[str, str]] = None,
                        json_payload: Optional[Dict[str, Any]] = None,
                        data: Optional[Union[str, bytes]] = None,
                        params: Optional[Dict[str, Any]] = None,
                        timeout: Optional[int] = None) -> HttpResponse:
        """Executa uma requisição HTTP com tratamento de erros"""
        
        timeout = timeout or self.default_timeout
        request_headers = {**self.session.headers}
        
        if headers:
            request_headers.update(headers)
        
        start_time = time.time()
        
        try:
            # Log da requisição
            logger.log_http_request(
                method=method,
                url=url,
                headers=request_headers,
                payload_size=len(json.dumps(json_payload)) if json_payload else 0
            )
            
            response = self.session.request(
                method=method,
                url=url,
                headers=request_headers,
                json=json_payload,
                data=data,
                params=params,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            body = self._parse_response_body(response)
            
            status = "success" if response.ok else "failed"
            
            # Log da resposta
            logger.log_http_request(
                method=method,
                url=url,
                status_code=response.status_code,
                duration=duration,
                response_size=len(response.text)
            )
            
            return HttpResponse(
                status_code=response.status_code,
                body=body,
                status=status,
                url=url,
                method=method,
                duration=duration,
                headers=dict(response.headers)
            )
            
        except requests.exceptions.Timeout:
            duration = time.time() - start_time
            logger.error(
                "http_timeout",
                method=method,
                url=url,
                timeout=timeout,
                duration=duration
            )
            
            return HttpResponse(
                status_code=0,
                body=None,
                status="timeout",
                url=url,
                method=method,
                duration=duration,
                error=f"Request timeout after {timeout}s"
            )
            
        except requests.exceptions.ConnectionError as e:
            duration = time.time() - start_time
            logger.error(
                "http_connection_error",
                method=method,
                url=url,
                error=str(e),
                duration=duration
            )
            
            return HttpResponse(
                status_code=0,
                body=None,
                status="connection_error",
                url=url,
                method=method,
                duration=duration,
                error=f"Connection error: {str(e)}"
            )
            
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            logger.error(
                "http_request_error",
                method=method,
                url=url,
                error=str(e),
                error_type=type(e).__name__,
                duration=duration
            )
            
            status_code = 0
            if hasattr(e, 'response') and e.response is not None:
                status_code = getattr(e.response, 'status_code', 0)
            
            return HttpResponse(
                status_code=status_code,
                body=None,
                status="error",
                url=url,
                method=method,
                duration=duration,
                error=f"Request failed: {str(e)}"
            )
    
    def request(self, 
                method: Union[str, HttpMethod],
                url: str,
                **kwargs) -> HttpResponse:
        """
        Executa uma requisição HTTP com retry automático.
        
        Args:
            method: Método HTTP
            url: URL da requisição
            **kwargs: Argumentos adicionais (headers, json, data, params, timeout)
        
        Returns:
            HttpResponse com o resultado da requisição
        """
        last_response = None
        
        for attempt in range(self.retry_count + 1):
            if attempt > 0:
                logger.info(
                    "http_retry",
                    method=method,
                    url=url,
                    attempt=attempt,
                    max_attempts=self.retry_count + 1
                )
                time.sleep(self.retry_delay * attempt)  # Backoff exponencial simples
            
            response = self._execute_request(method, url, **kwargs)
            last_response = response
            
            # Não faz retry em caso de sucesso ou erro do cliente
            if response.is_success or response.is_client_error:
                return response
            
            # Só faz retry em erros de servidor ou timeout
            if attempt < self.retry_count and (response.is_server_error or response.status_code == 0):
                continue
            
            return response
        
        return last_response
    
    def get(self, url: str, **kwargs) -> HttpResponse:
        """Executa requisição GET"""
        return self.request(HttpMethod.GET, url, **kwargs)
    
    def post(self, url: str, **kwargs) -> HttpResponse:
        """Executa requisição POST"""
        return self.request(HttpMethod.POST, url, **kwargs)
    
    def put(self, url: str, **kwargs) -> HttpResponse:
        """Executa requisição PUT"""
        return self.request(HttpMethod.PUT, url, **kwargs)
    
    def delete(self, url: str, **kwargs) -> HttpResponse:
        """Executa requisição DELETE"""
        return self.request(HttpMethod.DELETE, url, **kwargs)
    
    def patch(self, url: str, **kwargs) -> HttpResponse:
        """Executa requisição PATCH"""
        return self.request(HttpMethod.PATCH, url, **kwargs)
    
    def close(self):
        """Fecha a sessão HTTP"""
        self.session.close()
    
    def __enter__(self):
        """Suporte para context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Fecha a sessão ao sair do context manager"""
        self.close()