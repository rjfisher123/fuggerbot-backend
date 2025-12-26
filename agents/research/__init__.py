"""
Research Loop Agents for War Games Learning System.

Transforms deterministic backtests into a learning-capable research engine.
Maintains determinism while enabling comparative learning across scenarios.
"""
from agents.research.scenario_generator import ScenarioGenerator, ScenarioDefinition, get_scenario_generator
from agents.research.meta_evaluator import MetaEvaluator, ScenarioComparison, get_meta_evaluator
from agents.research.memory_agent import MemoryAgent, StrategyInsight, InsightConfidence, get_memory_agent
from agents.research.proposal_agent import ProposalAgent, ExperimentProposal, get_proposal_agent
from agents.research.regime_ontology import RegimeOntology, RegimeClassification, get_regime_ontology

__all__ = [
    "ScenarioGenerator",
    "ScenarioDefinition",
    "get_scenario_generator",
    "MetaEvaluator",
    "ScenarioComparison",
    "get_meta_evaluator",
    "MemoryAgent",
    "StrategyInsight",
    "InsightConfidence",
    "get_memory_agent",
    "ProposalAgent",
    "ExperimentProposal",
    "get_proposal_agent",
    "RegimeOntology",
    "RegimeClassification",
    "get_regime_ontology",
]

