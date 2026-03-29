from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel
import typer
import os

load_dotenv()

app_instance = typer.Typer()

class HyperParams(BaseModel):
    name: str = ".runs"
    run_dir: str = ".runs"
    iterations: int = 100
    action_limits: int = 4

hyper_params = HyperParams()

@app_instance.callback()
def init_hyper_params(
    run_dir: str = typer.Option(HyperParams.DEFAULT_RUN_DIR, "--run-dir", help="Directory to store run results"),
    iterations: int = typer.Option(HyperParams.DEFAULT_ITERATIONS, "--iterations", help="Budget of iterations to a run"),
    action_limits: int = typer.Option(HyperParams.DEFAULT_ACTION_LIMITS, "--action-limits", help="Action limits of each layer") 
):
    logger.info("Initializing hyper params")
    logger.debug(f"[param] run_dir: {run_dir}")
    logger.debug(f"[param] iterations: {iterations}")
    logger.debug(f"[param] action_limits: {action_limits}")
    hyper_params.run_dir = run_dir
    hyper_params.iterations = iterations
    hyper_params.action_limits = action_limits

@app_instance.command()
def generate(research_task: str):
    logger.opt(colors=True).info(f"Research task is: <green>{research_task}</green>")

@app_instance.command()
def dummy():
    logger.info("Dummy command")
