#!/usr/bin/env python3
"""
main orchestration script for kasparro agentic fb analyst
usage: python run.py "analyze roas drop in january"
"""
import sys
import yaml
import json
from pathlib import Path

from src.orchestrator.agent_graph import AgentOrchestrator


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py 'Your analysis query'")
        print("\nExample queries:")
        print("  python run.py 'Analyze overall ROAS performance'")
        print("  python run.py 'Why did CTR drop? Generate new creatives for low performers'")
        print("  python run.py 'Compare video vs image creative performance'")
        sys.exit(1)
    
    query = sys.argv[1]
    
    # load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # initialize orchestrator
    print("=" * 60)
    print("Kasparro Agentic FB Analyst")
    print("=" * 60)
    print(f"Query: {query}")
    print(f"Model: {config['llm']['model']}")
    print("-" * 60)
    
    try:
        # create orchestrator and run analysis
        orchestrator = AgentOrchestrator(config)
        results = orchestrator.run(query)
        
        # print the report
        print("\n" + "=" * 60)
        print("ANALYSIS REPORT")
        print("=" * 60)
        print(results['report'])
        
        # save results
        output_dir = Path(config['output']['reports_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # save insights json
        insights_path = output_dir / "insights.json"
        with open(insights_path, 'w') as f:
            json.dump(results['insights'], f, indent=2, default=str)
        
        # save creatives json
        creatives_path = output_dir / "creatives.json"
        with open(creatives_path, 'w') as f:
            json.dump(results['creatives'], f, indent=2, default=str)
        
        # save markdown report
        report_path = output_dir / "report.md"
        with open(report_path, 'w') as f:
            f.write(results['report'])
        
        print(f"\nResults saved to {output_dir}/")
        print(f"   - Report: report.md")
        print(f"   - Insights: insights.json")
        print(f"   - Creatives: creatives.json")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()