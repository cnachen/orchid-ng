from dotenv import load_dotenv
from loguru import logger
import typer

from orchid_ng.services.params import ParamsService

load_dotenv()

app_instance = typer.Typer()


@app_instance.callback()
def init_params_service(
    run_dir: str = typer.Option(
        ParamsService().run_dir,
        "--run-dir",
        help="Directory to store run results",
    ),
    iterations: int = typer.Option(
        ParamsService().iterations,
        "--iterations",
        help="Budget of iterations to a run",
    ),
    action_limits: int = typer.Option(
        ParamsService().action_limits,
        "--action-limits",
        help="Action limits of each layer",
    ),
):
    logger.info("Initializing ParamsService")
    logger.debug(f"[param] run_dir: {run_dir}")
    logger.debug(f"[param] iterations: {iterations}")
    logger.debug(f"[param] action_limits: {action_limits}")

    ParamsService().run_dir = run_dir
    ParamsService().iterations = iterations
    ParamsService().action_limits = action_limits


@app_instance.command()
def generate(research_task: str):
    logger.opt(colors=True).info(f"Research task is: <green>{research_task}</green>")


@app_instance.command()
def dummy():
    logger.info("Dummy command")
