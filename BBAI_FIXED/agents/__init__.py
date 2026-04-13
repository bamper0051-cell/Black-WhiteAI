"""
agents/ — All BlackBugsAI agents
Factory function creates agent instances by name.
"""
from agents.neo import AgentNeo
from agents.matrix import AgentMatrix
from agents.smith import AgentSmith
from agents.tanker import AgentTanker
from agents.anderson import AgentAnderson
from agents.pythia import AgentPythia
from agents.operator import AgentOperator

AGENT_MAP = {
    "neo":      AgentNeo,
    "matrix":   AgentMatrix,
    "smith":    AgentSmith,
    "tanker":   AgentTanker,
    "anderson": AgentAnderson,
    "pythia":   AgentPythia,
    "operator": AgentOperator,
}

AGENT_INFO = {name: {"name": cls.NAME, "emoji": cls.EMOJI, "modes": cls.MODES,
                       "access": cls.ACCESS, "desc": cls.__doc__ or ""}
              for name, cls in AGENT_MAP.items()}


def create_agent(name: str, mode: str = "auto"):
    """Factory: create agent instance by name."""
    cls = AGENT_MAP.get(name)
    if cls:
        return cls()
    return None
