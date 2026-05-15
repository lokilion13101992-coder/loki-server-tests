from agents.core.base import BaseAgent

class ResearchAgent(BaseAgent):
    def run(self, task: str):
        return f"[RESEARCH SIMULATION] searching: {task}"
