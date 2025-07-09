from functools import partial
from typing import Generator, List, Optional
import multiprocessing as mp

from fraim.config.config import Config
from fraim.core.contextuals.code import CodeChunk
from fraim.observability.manager import initialize_worker
from fraim.outputs import sarif
from fraim.workflows import WorkflowRegistry


def run_workflows(code_chunk: CodeChunk, config: Config, workflows_to_run: List[str]) -> List[sarif.Result]:
    """Run all specified workflows on the given data."""
    all_results = []
    for workflow in workflows_to_run:
        try:
            if WorkflowRegistry.is_workflow_available(workflow):
                results = WorkflowRegistry.execute_workflow(
                    workflow, code=code_chunk, config=config)
                all_results.extend(results)
            else:
                config.logger.warning(
                    f"Workflow '{workflow}' not available in registry")
        except Exception as e:
            config.logger.error(
                f"Error running {workflow} workflow on {code_chunk.description}: {str(e)}")
            continue

    return all_results


def run_parallel_workflows_on_chunks(chunks: Generator[CodeChunk, None, None], config: Config, workflows_to_run: List[str], observability_backends: Optional[List[str]]) -> List[sarif.Result]:
    results: List[sarif.Result] = []
    try:
        chunk_count = 0
        # TODO: actually test that multiprocessing has a measurable impact here.
        with mp.Pool(
            processes=config.processes, initializer=initialize_worker, initargs=(
                config, observability_backends)
        ) as pool:
            # This must be partial because mp serializes the function.
            # TODO: actually test that multiprocessing has a measurable impact here.
            task = partial(run_workflows, config=config,
                           workflows_to_run=workflows_to_run)

            for chunk_results in pool.imap_unordered(task, chunks):
                chunk_count += 1
                results.extend(chunk_results)
        config.logger.info(
            f"Completed processing {chunk_count} total chunks")
    except Exception as mp_error:
        config.logger.error(
            f"Error during multiprocessing: {str(mp_error)}")

    return results
