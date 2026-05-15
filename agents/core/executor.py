from agents.router.router import TaskRouter
from agents.core.registry import AgentRegistry


class Executor:
    def __init__(self):
        self.router = TaskRouter()
        self.registry = AgentRegistry()

    def execute(self, task: str):
        agent_name = self.router.route(task)
        agent = self.registry.get(agent_name)

        result = agent.run(task)

        return {
            "task": task,
            "agent": agent_name,
            "result": result
        }
