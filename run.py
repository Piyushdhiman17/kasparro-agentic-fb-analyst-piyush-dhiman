#!/usr/bin/env python3
"""
Main orchestration script for Kasparro Agentic FB Analyst
Usage: python run.py "Analyze ROAS drop in January"
"""
import sys
import yaml

def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py 'Your analysis query'")
        sys.exit(1)
    
    query = sys.argv[1]
    
    # load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # initialize orchestrator
    print(f"Starting Kasparro Agentic FB Analyst")
    print(f"Query: {query}")
    print(f"Model: {config['llm']['model']}")
    print("-" * 60)
    
    # simulate orchestration process
    print("Analyzing data...")

if __name__ == "__main__":
    main()