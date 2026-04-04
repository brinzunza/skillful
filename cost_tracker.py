"""
Cost tracking for OpenAI API usage.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional


# Pricing per 1M tokens (as of 2024-2025)
# Source: https://openai.com/pricing
PRICING = {
    "gpt-4o": {
        "input": 2.50,   # $2.50 per 1M input tokens
        "output": 10.00  # $10.00 per 1M output tokens
    },
    "gpt-4o-mini": {
        "input": 0.150,  # $0.15 per 1M input tokens
        "output": 0.600  # $0.60 per 1M output tokens
    },
    "gpt-4-turbo": {
        "input": 10.00,
        "output": 30.00
    },
    "gpt-4": {
        "input": 30.00,
        "output": 60.00
    },
    "gpt-3.5-turbo": {
        "input": 0.50,
        "output": 1.50
    }
}

COST_FILE = ".skillful/costs.json"


class CostTracker:
    """Tracks OpenAI API costs."""

    def __init__(self):
        """Initialize cost tracker."""
        self.session_costs = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self._ensure_cost_file()

    def _ensure_cost_file(self):
        """Ensure cost tracking directory exists."""
        os.makedirs(os.path.dirname(COST_FILE), exist_ok=True)

    def track_request(self, model: str, input_tokens: int, output_tokens: int):
        """
        Track a single API request.

        Args:
            model: Model name (e.g., "gpt-4o-mini")
            input_tokens: Number of input tokens (prompt)
            output_tokens: Number of output tokens (completion)
        """
        # Get pricing for model
        pricing = self._get_pricing(model)

        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        # Track in session
        self.session_costs.append({
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        })

        # Update totals
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += total_cost

    def _get_pricing(self, model: str) -> Dict[str, float]:
        """
        Get pricing for a model.

        Args:
            model: Model name

        Returns:
            Pricing dictionary with 'input' and 'output' keys
        """
        # Normalize model name
        model_key = model.lower()

        # Check exact match
        if model_key in PRICING:
            return PRICING[model_key]

        # Check if model name starts with known prefix
        for key in PRICING:
            if model_key.startswith(key):
                return PRICING[key]

        # Default to gpt-4o-mini pricing (conservative)
        return PRICING["gpt-4o-mini"]

    def get_session_summary(self) -> Dict:
        """
        Get summary of current session costs.

        Returns:
            Dictionary with session cost summary
        """
        if not self.session_costs:
            return {
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0.0
            }

        return {
            "total_requests": len(self.session_costs),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost": self.total_cost,
            "cost_per_request": self.total_cost / len(self.session_costs) if self.session_costs else 0,
            "requests": self.session_costs
        }

    def save_session_costs(self):
        """Save session costs to persistent storage."""
        if not self.session_costs:
            return

        # Load existing data
        all_sessions = self._load_all_costs()

        # Add current session
        session = {
            "start_time": self.session_costs[0]["timestamp"],
            "end_time": self.session_costs[-1]["timestamp"],
            "summary": self.get_session_summary(),
            "requests": self.session_costs
        }
        all_sessions.append(session)

        # Save back
        try:
            with open(COST_FILE, 'w') as f:
                json.dump(all_sessions, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save cost data: {e}")

    def _load_all_costs(self) -> List[Dict]:
        """Load all historical cost data."""
        if not os.path.exists(COST_FILE):
            return []

        try:
            with open(COST_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def get_historical_summary(self) -> Dict:
        """
        Get summary of all historical costs.

        Returns:
            Dictionary with lifetime cost summary
        """
        all_sessions = self._load_all_costs()

        if not all_sessions:
            return {
                "total_sessions": 0,
                "total_cost": 0.0,
                "total_tokens": 0
            }

        total_cost = sum(s["summary"]["total_cost"] for s in all_sessions)
        total_tokens = sum(s["summary"]["total_tokens"] for s in all_sessions)

        return {
            "total_sessions": len(all_sessions),
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "average_cost_per_session": total_cost / len(all_sessions) if all_sessions else 0
        }

    def format_cost_report(self, include_details: bool = False) -> str:
        """
        Format a cost report for display.

        Args:
            include_details: Include per-request details

        Returns:
            Formatted cost report string
        """
        summary = self.get_session_summary()

        report = []
        report.append("=" * 60)
        report.append("COST REPORT - Current Session")
        report.append("=" * 60)
        report.append(f"Total Requests: {summary['total_requests']}")
        report.append(f"Total Tokens: {summary['total_tokens']:,}")
        report.append(f"  Input:  {summary['total_input_tokens']:,} tokens")
        report.append(f"  Output: {summary['total_output_tokens']:,} tokens")
        report.append(f"Total Cost: ${summary['total_cost']:.4f}")

        if summary['total_requests'] > 0:
            report.append(f"Average Cost per Request: ${summary['cost_per_request']:.4f}")

        if include_details and self.session_costs:
            report.append("\nPer-Request Details:")
            report.append("-" * 60)
            for i, req in enumerate(self.session_costs, 1):
                report.append(f"\nRequest {i}:")
                report.append(f"  Model: {req['model']}")
                report.append(f"  Tokens: {req['input_tokens'] + req['output_tokens']:,} "
                            f"({req['input_tokens']:,} in + {req['output_tokens']:,} out)")
                report.append(f"  Cost: ${req['total_cost']:.4f}")

        # Historical summary
        historical = self.get_historical_summary()
        if historical['total_sessions'] > 0:
            report.append("\n" + "=" * 60)
            report.append("HISTORICAL SUMMARY")
            report.append("=" * 60)
            report.append(f"Total Sessions: {historical['total_sessions']}")
            report.append(f"Lifetime Cost: ${historical['total_cost']:.2f}")
            report.append(f"Lifetime Tokens: {historical['total_tokens']:,}")
            report.append(f"Average per Session: ${historical['average_cost_per_session']:.4f}")

        report.append("=" * 60)

        return "\n".join(report)
