from agents.core.coder import CoderAgent
from agents.core.research import ResearchAgent
from agents.core.memory import MemoryAgent
from agents.core.general import GeneralAgent
from agents.loki.loki_agent import LokiAgent


class AgentRegistry:
    def __init__(self):
        self.agents = {
            "coder_agent": CoderAgent(),
            "research_agent": ResearchAgent(),
            "memory_agent": MemoryAgent(),
            "general_agent": GeneralAgent(),
            "loki_agent": LokiAgent(),
        }

    def get(self, name: str):
        return self.agents.get(name, self.agents["general_agent"])

    def list_agents(self):
        return list(self.agents.keys())
