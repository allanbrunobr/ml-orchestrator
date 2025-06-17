"""
Flow Executor - Responsável por executar fluxos com gerenciamento de paralelismo.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
from datetime import datetime
import traceback

from config.settings import FlowStep, StepStatus
from core.models import StepResult, ExecutionContext
from core.step_executor import StepExecutor
from utils.logger import get_logger


logger = get_logger("flow_executor")


class FlowExecutor:
    """Executor de fluxos com suporte a paralelismo controlado"""
    
    def __init__(self, max_workers: int = 4):
        """
        Inicializa o executor.
        
        Args:
            max_workers: Número máximo de workers para execução paralela
        """
        self.step_executor = StepExecutor()
        self.max_workers = max_workers
        self.logger = logger
    
    def execute_flow(self, 
                    steps: List[FlowStep], 
                    context: ExecutionContext) -> List[StepResult]:
        """
        Executa um fluxo completo com paralelismo controlado.
        
        Args:
            steps: Lista de steps a executar
            context: Contexto de execução
            
        Returns:
            Lista de resultados da execução
        """
        self.logger.info(
            "flow_execution_start",
            execution_id=context.execution_id,
            flow_name=context.flow_name,
            total_steps=len(steps)
        )
        
        # Agrupa steps por possibilidade de paralelismo
        step_groups = self._group_steps_by_parallelism(steps)
        
        self.logger.debug(
            "step_groups_created",
            execution_id=context.execution_id,
            group_count=len(step_groups),
            groups=[{"size": len(g), "parallel": g[0].parallel_group if g else None} for g in step_groups]
        )
        
        results = []
        
        # Executa cada grupo de steps
        for group_index, group in enumerate(step_groups):
            self.logger.debug(
                "executing_step_group",
                execution_id=context.execution_id,
                group_index=group_index,
                group_size=len(group),
                is_parallel=len(group) > 1
            )
            
            if len(group) == 1:
                # Execução sequencial
                result = self._execute_single_step(group[0], context)
                results.append(result)
                context.add_result(result)
                
                # Se houve erro crítico, interrompe o fluxo
                if result.status == StepStatus.CRITICAL_ERROR:
                    self.logger.error(
                        "flow_aborted",
                        execution_id=context.execution_id,
                        reason="critical_error",
                        failed_step=result.step_name
                    )
                    break
            else:
                # Execução paralela
                group_results = self._execute_parallel_steps(group, context)
                results.extend(group_results)
                
                # Adiciona resultados ao contexto
                for result in group_results:
                    context.add_result(result)
                
                # Se algum step paralelo teve erro crítico, interrompe
                if any(r.status == StepStatus.CRITICAL_ERROR for r in group_results):
                    self.logger.error(
                        "flow_aborted",
                        execution_id=context.execution_id,
                        reason="critical_error_in_parallel_group",
                        failed_steps=[r.step_name for r in group_results if r.status == StepStatus.CRITICAL_ERROR]
                    )
                    break
        
        self.logger.info(
            "flow_execution_end",
            execution_id=context.execution_id,
            flow_name=context.flow_name,
            total_results=len(results),
            successful_steps=len([r for r in results if r.status == StepStatus.SUCCESS]),
            failed_steps=len([r for r in results if r.status in [StepStatus.FAILED, StepStatus.CRITICAL_ERROR]])
        )
        
        return results
    
    def _group_steps_by_parallelism(self, steps: List[FlowStep]) -> List[List[FlowStep]]:
        """
        Agrupa steps que podem executar em paralelo.
        
        Steps com o mesmo parallel_group podem executar juntos.
        Steps sem parallel_group executam sequencialmente.
        
        Args:
            steps: Lista de steps
            
        Returns:
            Lista de grupos de steps
        """
        groups = []
        current_group = []
        current_parallel_group = None
        
        for step in steps:
            if step.parallel_group:
                # Step faz parte de um grupo paralelo
                if step.parallel_group == current_parallel_group:
                    # Adiciona ao grupo atual
                    current_group.append(step)
                else:
                    # Novo grupo paralelo
                    if current_group:
                        groups.append(current_group)
                    current_group = [step]
                    current_parallel_group = step.parallel_group
            else:
                # Step sequencial
                if current_group:
                    groups.append(current_group)
                    current_group = []
                    current_parallel_group = None
                groups.append([step])
        
        # Adiciona último grupo se existir
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _execute_single_step(self, 
                           step: FlowStep, 
                           context: ExecutionContext) -> StepResult:
        """
        Executa um único step.
        
        Args:
            step: Step a executar
            context: Contexto de execução
            
        Returns:
            Resultado da execução
        """
        self.logger.debug(
            "executing_single_step",
            execution_id=context.execution_id,
            step_name=step.name
        )
        
        return self.step_executor.execute_step(step, context)
    
    def _execute_parallel_steps(self, 
                              steps: List[FlowStep],
                              context: ExecutionContext) -> List[StepResult]:
        """
        Executa múltiplos steps em paralelo.
        
        Args:
            steps: Steps a executar em paralelo
            context: Contexto de execução
            
        Returns:
            Lista de resultados
        """
        self.logger.info(
            "executing_parallel_group",
            execution_id=context.execution_id,
            step_names=[s.name for s in steps],
            parallel_group=steps[0].parallel_group if steps else None
        )
        
        results = []
        
        with ThreadPoolExecutor(max_workers=min(len(steps), self.max_workers)) as executor:
            # Submete todos os steps para execução
            future_to_step = {
                executor.submit(self.step_executor.execute_step, step, context): step
                for step in steps
            }
            
            # Coleta resultados conforme completam
            for future in as_completed(future_to_step):
                step = future_to_step[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    self.logger.debug(
                        "parallel_step_completed",
                        execution_id=context.execution_id,
                        step_name=step.name,
                        status=result.status
                    )
                    
                except Exception as e:
                    # Captura exceções não tratadas
                    error_msg = str(e)
                    error_details = traceback.format_exc()
                    
                    self.logger.error(
                        "parallel_step_exception",
                        execution_id=context.execution_id,
                        step_name=step.name,
                        error=error_msg,
                        traceback=error_details
                    )
                    
                    # Cria resultado de erro
                    result = StepResult(
                        step_name=step.name,
                        status=StepStatus.CRITICAL_ERROR,
                        duration=0.0,
                        started_at=datetime.utcnow(),
                        completed_at=datetime.utcnow(),
                        error=f"Unhandled exception: {error_msg}",
                        error_details=error_details
                    )
                    results.append(result)
        
        self.logger.info(
            "parallel_group_completed",
            execution_id=context.execution_id,
            total_steps=len(steps),
            successful=len([r for r in results if r.status == StepStatus.SUCCESS]),
            failed=len([r for r in results if r.status != StepStatus.SUCCESS])
        )
        
        return results
    
    def execute_flow_async(self, 
                          steps: List[FlowStep], 
                          context: ExecutionContext) -> List[StepResult]:
        """
        Versão assíncrona da execução de fluxo (para futura migração).
        
        Por enquanto, apenas chama a versão síncrona.
        """
        return self.execute_flow(steps, context)