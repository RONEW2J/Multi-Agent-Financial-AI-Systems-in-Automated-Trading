"""
Agent modules for the Multi-Agent Trading System.

Each agent runs independently as a microservice:
- Market Agent (port 8000): Fetches market data and sends to Decision Agent
- Decision Agent (port 8001): Analyzes data with AI model and makes decisions
- Execution Agent (port 8002): Executes trades and records to database
"""

__all__ = ["market_agent", "decision_agent", "execution_agent"]
