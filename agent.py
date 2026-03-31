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
from safety import SafetyMonitor, needs_user_confirmation

# Load environment variables from .env file
load_dotenv()


class AutonomousAgent:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini", enable_safety: bool = True):
        """
        Initialize the autonomous agent.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use
            enable_safety: Enable safety checks (default: True)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found. Please set it in .env file or environment variables")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.conversation_history = []
        self.max_iterations = 20  # Prevent infinite loops
        self.enable_safety = enable_safety
        self.safety_monitor = SafetyMonitor() if enable_safety else None

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

        # Safety check before execution
        if self.enable_safety:
            is_allowed, reason = self.safety_monitor.check_operation(skill, args)
            if not is_allowed:
                print(f"\nSAFETY BLOCK: {reason}")
                return f"BLOCKED: {reason}"

        # Check if user confirmation is required
        if needs_user_confirmation(skill, args):
            if not self._get_user_confirmation(skill, args):
                print(f"\nUSER DENIED: Operation cancelled by user")
                return "DENIED: User cancelled the operation"

        result = execute_skill(skill, **args)
        return result

    def _get_user_confirmation(self, skill: str, args: dict) -> bool:
        """
        Ask user for confirmation before executing a sensitive operation.

        Args:
            skill: Name of the skill
            args: Arguments for the skill

        Returns:
            True if user confirms, False otherwise
        """
        print(f"\n{'='*60}")
        print(f"CONFIRMATION REQUIRED")
        print(f"{'='*60}")
        print(f"Skill: {skill}")
        print(f"Arguments: {json.dumps(args, indent=2)}")
        print(f"{'='*60}")

        while True:
            response = input("Allow this operation? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            else:
                print("Please answer 'yes' or 'no'")


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

        # Print safety report if enabled
        if self.enable_safety:
            self._print_safety_report()

    def _print_safety_report(self):
        """Print a safety report after agent execution."""
        report = self.safety_monitor.get_safety_report()

        print(f"\n{'='*60}")
        print("SAFETY REPORT")
        print(f"{'='*60}")
        print(f"Total operations: {report['total_operations']}")
        print(f"Blocked operations: {report['violations']}")
        print(f"\nRisk distribution:")
        for risk_level, count in report['risk_distribution'].items():
            if count > 0:
                print(f"  {risk_level.upper()}: {count}")

        if report['violation_details']:
            print(f"\nBlocked operations:")
            for violation in report['violation_details']:
                print(f"  - {violation}")
        print(f"{'='*60}\n")


class SkillfulTerminal:
    """Interactive terminal interface for Skillful agent."""

    def __init__(self):
        self.agent = AutonomousAgent()
        self.running = True

    def print_banner(self):
        """Print welcome banner."""
        print("\n" + "="*60)
        print("  SKILLFUL - Autonomous Agent Terminal")
        print("="*60)
        print("Type /help for available commands")
        print("Type /exit to quit")
        print("="*60 + "\n")

    def handle_help(self, args):
        """Show help information."""
        print("\n" + "="*60)
        print("AVAILABLE COMMANDS")
        print("="*60)
        print("/order <task>  - Give the agent a task to complete")
        print("/skills        - List all available skills")
        print("/help          - Show this help message")
        print("/clear         - Clear the screen")
        print("/history       - Show conversation history")
        print("/reset         - Reset the agent (clear history)")
        print("/exit          - Exit the terminal")
        print("="*60 + "\n")

    def handle_skills(self, args):
        """List all available skills."""
        from skills import SKILLS
        print("\n" + "="*60)
        print("AVAILABLE SKILLS")
        print("="*60)
        for name, func in SKILLS.items():
            doc = func.__doc__.split('\n')[1].strip() if func.__doc__ else "No description"
            print(f"• {name}")
            print(f"  {doc}")
        print("="*60 + "\n")

    def handle_order(self, args):
        """Execute an agent task."""
        if not args:
            print("Error: Please provide a task")
            print("Example: /order create a file called hello.txt\n")
            return

        goal = " ".join(args)
        print(f"\nExecuting task: {goal}\n")
        self.agent.run(goal)

    def handle_clear(self, args):
        """Clear the screen."""
        os.system('clear' if os.name != 'nt' else 'cls')
        self.print_banner()

    def handle_history(self, args):
        """Show conversation history."""
        if not self.agent.conversation_history:
            print("\nNo conversation history yet\n")
            return

        print("\n" + "="*60)
        print("CONVERSATION HISTORY")
        print("="*60)
        for i, msg in enumerate(self.agent.conversation_history[-10:], 1):
            role = msg['role'].upper()
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            print(f"\n[{i}] {role}:")
            print(f"    {content}")
        print("="*60 + "\n")

    def handle_reset(self, args):
        """Reset the agent."""
        self.agent = AutonomousAgent()
        print("\nAgent reset. Conversation history cleared.\n")

    def handle_exit(self, args):
        """Exit the terminal."""
        print("\nGoodbye!\n")
        self.running = False

    def parse_command(self, user_input):
        """Parse user input into command and arguments."""
        parts = user_input.strip().split()
        if not parts:
            return None, []

        command = parts[0].lower()
        args = parts[1:]
        return command, args

    def run(self):
        """Run the interactive terminal."""
        self.print_banner()

        while self.running:
            try:
                user_input = input("skillful> ").strip()

                if not user_input:
                    continue

                command, args = self.parse_command(user_input)

                # Handle commands
                if command == "/help":
                    self.handle_help(args)
                elif command == "/skills":
                    self.handle_skills(args)
                elif command == "/order":
                    self.handle_order(args)
                elif command == "/clear":
                    self.handle_clear(args)
                elif command == "/history":
                    self.handle_history(args)
                elif command == "/reset":
                    self.handle_reset(args)
                elif command == "/exit" or command == "/quit":
                    self.handle_exit(args)
                else:
                    print(f"Unknown command: {command}")
                    print("Type /help for available commands\n")

            except KeyboardInterrupt:
                print("\n\nInterrupted. Type /exit to quit.\n")
            except EOFError:
                print("\n")
                self.handle_exit([])
            except Exception as e:
                print(f"\nError: {str(e)}\n")


def main():
    # Check if running in interactive mode or single command mode
    if len(sys.argv) < 2:
        # Interactive terminal mode
        terminal = SkillfulTerminal()
        terminal.run()
    else:
        # Single command mode (backwards compatibility)
        goal = " ".join(sys.argv[1:])
        agent = AutonomousAgent()
        agent.run(goal)


if __name__ == "__main__":
    main()
