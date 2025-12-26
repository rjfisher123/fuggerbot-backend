#!/usr/bin/env python
"""
Test script for Research Loop system.

Demonstrates the learning-capable research engine in action.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.research.scenario_generator import get_scenario_generator
from agents.research.meta_evaluator import get_meta_evaluator
from agents.research.memory_agent import get_memory_agent
from agents.research.proposal_agent import get_proposal_agent
from daemon.research_loop import get_research_loop


def test_scenario_generator():
    """Test scenario generator."""
    print("\n" + "="*60)
    print("Testing Scenario Generator")
    print("="*60)
    
    generator = get_scenario_generator()
    
    # Generate baseline
    baseline = generator.generate_baseline_scenario()
    print(f"\n✅ Generated baseline scenario:")
    print(f"   ID: {baseline.scenario_id}")
    print(f"   Name: {baseline.scenario_name}")
    print(f"   Symbols: {baseline.symbols}")
    print(f"   Param sets: {list(baseline.param_sets.keys())}")
    
    # Generate variants
    variants = generator.generate_scenario_variants(baseline)
    print(f"\n✅ Generated {len(variants)} variant scenarios")
    for i, variant in enumerate(variants[:3], 1):
        print(f"   {i}. {variant.scenario_name} (ID: {variant.scenario_id[:8]}...)")
    
    return baseline, variants


def test_memory_agent():
    """Test memory agent."""
    print("\n" + "="*60)
    print("Testing Memory Agent")
    print("="*60)
    
    memory = get_memory_agent()
    
    # Add a test insight
    insight = memory.add_insight(
        insight_type="winning_pattern",
        description="Trust threshold >0.65 improves drawdown in volatile regimes",
        scenario_ids=["test_1", "test_2"],
        regimes=["Inflation Shock 2022"],
        evidence_metrics={"return_delta": 2.3, "drawdown_delta": -5.1},
        confidence=0.75
    )
    
    print(f"\n✅ Added insight: {insight.insight_id}")
    print(f"   Description: {insight.description}")
    print(f"   Confidence: {insight.confidence}")
    
    # Get insights
    insights = memory.get_insights_for_scenario_generation()
    print(f"\n✅ Memory contains:")
    print(f"   Winning patterns: {len(insights['winning_patterns'])}")
    print(f"   Failure modes: {len(insights['failure_modes'])}")
    print(f"   Regime heuristics: {len(insights['regime_heuristics'])}")
    
    return memory


def test_proposal_agent():
    """Test proposal agent."""
    print("\n" + "="*60)
    print("Testing Proposal Agent")
    print("="*60)
    
    proposal_agent = get_proposal_agent()
    memory = get_memory_agent()
    
    # Get insights
    insights = memory.get_insights_for_scenario_generation()
    
    # Generate proposals
    proposals = proposal_agent.generate_proposals(
        existing_scenarios=[],
        memory_insights=insights,
        limit=3
    )
    
    print(f"\n✅ Generated {len(proposals)} proposals:")
    for i, proposal in enumerate(proposals, 1):
        print(f"\n   {i}. {proposal.title}")
        print(f"      Type: {proposal.proposal_type}")
        print(f"      Priority: {proposal.priority}/10")
        print(f"      Expected info gain: {proposal.expected_info_gain:.2f}")
        print(f"      Reasoning: {proposal.reasoning[:80]}...")
    
    return proposals


def test_research_loop():
    """Test research loop (without running full simulation)."""
    print("\n" + "="*60)
    print("Testing Research Loop Orchestrator")
    print("="*60)
    
    loop = get_research_loop()
    
    # Get current insights
    insights = loop.get_current_insights()
    print(f"\n✅ Current research state:")
    print(f"   Total insights: {insights['total_insights']}")
    print(f"   Winning patterns: {insights['winning_patterns']}")
    print(f"   Failure modes: {insights['failure_modes']}")
    print(f"   Regime heuristics: {insights['regime_heuristics']}")
    
    print(f"\n✅ Research loop initialized and ready!")
    print(f"   Results store: {loop.results_store_path}")
    print(f"   Memory store: {loop.memory_agent.memory_store_path}")
    
    return loop


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("FuggerBot Research Loop Test Suite")
    print("="*60)
    
    try:
        # Test scenario generator
        baseline, variants = test_scenario_generator()
        
        # Test memory agent
        memory = test_memory_agent()
        
        # Test proposal agent
        proposals = test_proposal_agent()
        
        # Test research loop
        loop = test_research_loop()
        
        print("\n" + "="*60)
        print("✅ All Tests Passed!")
        print("="*60)
        print("\nResearch Loop system is ready for use.")
        print("\nNext steps:")
        print("  1. Run: loop.run_iteration() to execute a research iteration")
        print("  2. Check insights: loop.get_current_insights()")
        print("  3. View memory: data/strategy_memory.json")
        print("  4. View results: data/research_results/")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

