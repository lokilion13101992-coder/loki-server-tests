from agents.core.base import BaseAgent

class CoderAgent(BaseAgent):
    def run(self, task: str):
        return f"[CODER EXEC] {task}"
