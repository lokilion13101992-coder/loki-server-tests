from agents.core.base import BaseAgent

class MemoryAgent(BaseAgent):
    def run(self, task: str):
        return f"[MEMORY STORED] {task}"
