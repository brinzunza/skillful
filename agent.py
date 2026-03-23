#!/usr/bin/env python3
"""
A simple autonomous agent that can execute skills to achieve goals.
"""

import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI
from skills import get_skills_description, execute_skill

# Load environment variables from .env file
load_dotenv()


class AutonomousAgent:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        """
        Initialize the autonomous agent.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found. Please set it in .env file or environment variables")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.conversation_history = []
        self.max_iterations = 20  # Prevent infinite loops

    def think(self, goal: str, observation: str = None) -> dict:
        """
        Use the LLM to decide what action to take next.

        Args:
            goal: The goal to achieve
            observation: Result from the last action (if any)

        Returns:
            Dictionary with 'action', 'skill', 'args', and 'reasoning'
        """
        # Build the system prompt
        system_prompt = f"""You are an autonomous agent that can execute skills to achieve goals.

Available skills:
{get_skills_description()}

Your job is to:
1. Think about what needs to be done to achieve the goal
2. Choose the next skill to execute
3. Provide the arguments for that skill
4. Decide if the goal is complete

Respond ONLY with valid JSON in this exact format:
{{
    "reasoning": "Your thought process",
    "action": "execute" or "complete",
    "skill": "skill_name",
    "args": {{"param": "value"}}
}}

If the goal is achieved, set "action" to "complete" and omit "skill" and "args".
"""

        # Build the user message
        if observation:
            user_message = f"Goal: {goal}\n\nLast action result: {observation}\n\nWhat should I do next?"
        else:
            user_message = f"Goal: {goal}\n\nWhat should I do first?"

        # Get response from LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        # Add conversation history for context
        messages.extend(self.conversation_history[-6:])  # Keep last 3 exchanges
        messages.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7
        )

        # Parse the response
        content = response.choices[0].message.content.strip()

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            decision = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response was: {content}")
            decision = {
                "reasoning": "Failed to parse response",
                "action": "complete"
            }

        # Store in conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": content})

        return decision

    def act(self, decision: dict) -> str:
        """
        Execute the action decided by the LLM.

        Args:
            decision: Decision dictionary from think()

        Returns:
            Result of the action
        """
        if decision["action"] == "complete":
            return "GOAL_COMPLETE"

        skill = decision.get("skill")
        args = decision.get("args", {})

        if not skill:
            return "Error: No skill specified"

        result = execute_skill(skill, **args)
        return result

    def run(self, goal: str):
        """
        Run the agent to achieve the goal.

        Args:
            goal: The goal to achieve
        """
        print(f"\n{'='*60}")
        print(f"GOAL: {goal}")
        print(f"{'='*60}\n")

        observation = None

        for iteration in range(self.max_iterations):
            print(f"\n--- Iteration {iteration + 1} ---")

            # Think about what to do
            decision = self.think(goal, observation)

            print(f"\nReasoning: {decision.get('reasoning', 'N/A')}")
            print(f"Action: {decision.get('action', 'N/A')}")

            # Check if goal is complete
            if decision["action"] == "complete":
                print(f"\n{'='*60}")
                print("GOAL ACHIEVED!")
                print(f"{'='*60}\n")
                break

            # Execute the action
            skill = decision.get("skill", "N/A")
            args = decision.get("args", {})
            print(f"Executing: {skill}({args})")

            observation = self.act(decision)
            print(f"Result: {observation[:500]}...")  # Truncate long outputs

        else:
            print(f"\n{'='*60}")
            print("Max iterations reached. Goal may not be complete.")
            print(f"{'='*60}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python agent.py '<your goal here>'")
        print("Example: python agent.py 'create a file called test.txt with hello world'")
        sys.exit(1)

    goal = " ".join(sys.argv[1:])

    # Initialize and run the agent
    agent = AutonomousAgent()
    agent.run(goal)


if __name__ == "__main__":
    main()
