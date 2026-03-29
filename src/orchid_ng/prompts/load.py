from loguru import logger
from pathlib import Path

current_dir = Path(__file__).parent.resolve()

class PromptLoader:
    def __init__(self, prompt_dir: str = current_dir.as_posix()):
        self.prompt_dir = Path(prompt_dir)
    
    def load(self, prompt_file: str) -> str:
        prompt_path = self.prompt_dir / prompt_file

        # Add suffix if not provided
        if prompt_path.suffix != ".txt":
            prompt_path = prompt_path.with_suffix(".txt")

        # If prompt file does not exist, raise error
        try:
            with open(prompt_path, "r") as f:
                prompt = f.read()
        except FileNotFoundError:
            logger.error(f"Prompt file {prompt_file} not found.")
            raise
        return prompt
