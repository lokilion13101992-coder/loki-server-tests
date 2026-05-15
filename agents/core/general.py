from agents.core.base import BaseAgent

class GeneralAgent(BaseAgent):
    def run(self, task: str):
        return f"[GENERAL RESPONSE] {task}"
