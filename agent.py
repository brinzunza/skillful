#!/usr/bin/env python3
"""
A simple autonomous agent that can execute skills to achieve goals.
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from skills import get_skills_description, execute_skill
from safety import SafetyMonitor, needs_user_confirmation
from config import Config
from memory import Memory
from async_executor import AsyncExecutor
from cost_tracker import CostTracker

# Load environment variables from .env file
load_dotenv()


class AutonomousAgent:
    def __init__(self, api_key: str = None, config: Config = None, silent: bool = False):
        """
        Initialize the autonomous agent.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            config: Configuration object (creates default if None)
            silent: If True, suppress all output (for background tasks)
        """
        # Load or create config
        self.config = config or Config()

        # Setup API
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found. Please set it in .env file or environment variables")

        self.client = OpenAI(api_key=self.api_key)

        # Load config values
        self.model = self.config.get("model", "gpt-4o-mini")
        self.max_iterations = self.config.get("max_iterations", 20)
        self.temperature = self.config.get("temperature", 0.7)

        # Silent mode for background tasks
        self.silent = silent

        # Initialize components
        self.conversation_history = []
        self.enable_safety = self.config.get("safety.enabled", True)
        self.safety_monitor = SafetyMonitor() if self.enable_safety else None

        # Memory
        self.memory = Memory() if self.config.get("memory.enabled", True) else None

        # Cost tracking
        self.cost_tracker = CostTracker()

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

        # Stream the response
        if not self.silent:
            print("\n" + "="*60, flush=True)
            print("AGENT REASONING (streaming...)", flush=True)
            print("="*60, flush=True)

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            stream=True
        )

        # Collect streamed content
        content = ""
        input_tokens = 0
        output_tokens = 0
        in_json_block = False
        buffer = ""

        for chunk in stream:
            if chunk.choices[0].delta.content:
                chunk_content = chunk.choices[0].delta.content
                content += chunk_content

                if not self.silent:
                    buffer += chunk_content

                    # Detect JSON code blocks
                    if "```json" in buffer:
                        in_json_block = True
                        # Print what came before
                        before_json = buffer.split("```json")[0]
                        print(before_json, end='', flush=True)
                        print("\n[JSON Response]", flush=True)
                        buffer = ""
                    elif "```" in buffer and in_json_block:
                        in_json_block = False
                        buffer = ""
                    else:
                        # Stream character by character for smooth display
                        print(chunk_content, end='', flush=True)
                        buffer = ""

            # Track usage if available
            if hasattr(chunk, 'usage') and chunk.usage:
                input_tokens = chunk.usage.prompt_tokens
                output_tokens = chunk.usage.completion_tokens

        if not self.silent:
            print("\n" + "="*60 + "\n", flush=True)  # Close streaming section

        # Track API cost (estimate if usage not provided in stream)
        if input_tokens > 0 or output_tokens > 0:
            self.cost_tracker.track_request(
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
        else:
            # Estimate token usage (rough approximation: 1 token ≈ 4 chars)
            estimated_input = sum(len(m.get('content', '')) for m in messages) // 4
            estimated_output = len(content) // 4
            self.cost_tracker.track_request(
                model=self.model,
                input_tokens=estimated_input,
                output_tokens=estimated_output
            )

        # Parse the response
        content = content.strip()

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
                if not self.silent:
                    print(f"\nSAFETY BLOCK: {reason}")
                return f"BLOCKED: {reason}"

        # Check if user confirmation is required
        # In silent mode, auto-deny operations requiring confirmation
        if needs_user_confirmation(skill, args):
            if self.silent:
                return "DENIED: Background tasks cannot request user confirmation"
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
        if not self.silent:
            print(f"\n{'='*60}")
            print(f"GOAL: {goal}")
            print(f"{'='*60}\n")

        observation = None

        for iteration in range(self.max_iterations):
            if not self.silent:
                print(f"\n{'='*60}")
                print(f"ITERATION {iteration + 1}/{self.max_iterations}")
                print(f"{'='*60}")

            # Think about what to do (streams reasoning in real-time)
            decision = self.think(goal, observation)

            # Check if goal is complete
            if decision["action"] == "complete":
                if not self.silent:
                    print(f"\n{'='*60}")
                    print("GOAL ACHIEVED!")
                    print(f"{'='*60}\n")
                break

            # Execute the action
            skill = decision.get("skill", "N/A")
            args = decision.get("args", {})

            if not self.silent:
                print(f"\n[Executing: {skill}]")
                if args:
                    print(f"Arguments: {json.dumps(args, indent=2)}")

            observation = self.act(decision)

            if not self.silent:
                print(f"\n[Result]")
                # Truncate long outputs but show more context
                if len(observation) > 500:
                    print(f"{observation[:500]}...\n(truncated, {len(observation)} total chars)")
                else:
                    print(observation)

        else:
            if not self.silent:
                print(f"\n{'='*60}")
                print("Max iterations reached. Goal may not be complete.")
                print(f"{'='*60}\n")

        # Print safety report if enabled (not in silent mode)
        if self.enable_safety and not self.silent:
            self._print_safety_report()

        # Print cost report (not in silent mode)
        if not self.silent:
            self._print_cost_summary()

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

    def _print_cost_summary(self):
        """Print a cost summary after agent execution."""
        summary = self.cost_tracker.get_session_summary()

        if summary['total_requests'] == 0:
            return

        print(f"\n{'='*60}")
        print("COST SUMMARY")
        print(f"{'='*60}")
        print(f"API Requests: {summary['total_requests']}")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        print(f"  Input:  {summary['total_input_tokens']:,} tokens")
        print(f"  Output: {summary['total_output_tokens']:,} tokens")
        print(f"Session Cost: ${summary['total_cost']:.4f}")
        print(f"{'='*60}\n")


class SkillfulTerminal:
    """Interactive terminal interface for Skillful agent."""

    def __init__(self):
        self.config = Config()
        self.agent = AutonomousAgent(config=self.config)
        max_concurrent = self.config.get("async.max_concurrent_tasks", 3)
        self.async_executor = AsyncExecutor(max_concurrent=max_concurrent)
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
        print("/submit <task> - Submit a task to run in background")
        print("/tasks         - List all background tasks")
        print("/task <id>     - Check status of a specific task")
        print("/cancel <id>   - Cancel a running background task")
        print("/skills        - List all available skills")
        print("/help          - Show this help message")
        print("/clear         - Clear the screen")
        print("/history       - Show conversation history")
        print("/reset         - Reset the agent (clear history)")
        print("/save [name]   - Save current session")
        print("/load [id]     - Load a saved session")
        print("/sessions      - List all saved sessions")
        print("/config        - Show configuration")
        print("/cost          - Show detailed cost report")
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

    def handle_submit(self, args):
        """Submit a task to run in background."""
        if not args:
            print("Error: Please provide a task")
            print("Example: /submit create a file called hello.txt\n")
            return

        goal = " ".join(args)

        # Create a new agent instance for this background task
        def agent_runner(task_goal, output_queue):
            """Run agent in background and capture output."""
            try:
                # Create a fresh agent instance for this task in SILENT mode
                task_agent = AutonomousAgent(config=self.config, silent=True)
                output_queue.put(f"[{datetime.now().strftime('%H:%M:%S')}] Starting task: {task_goal}")
                task_agent.run(task_goal)
                output_queue.put(f"[{datetime.now().strftime('%H:%M:%S')}] Task completed successfully")
                return "SUCCESS"
            except Exception as e:
                output_queue.put(f"[{datetime.now().strftime('%H:%M:%S')}] Task failed: {str(e)}")
                raise

        task_id = self.async_executor.submit_task(goal, agent_runner)
        print(f"\n✓ Task submitted successfully")
        print(f"Task ID: {task_id}")
        print(f"Goal: {goal}")
        print(f"\nUse '/task {task_id}' to check status")
        print(f"Use '/tasks' to list all tasks\n")

    def handle_tasks(self, args):
        """List all background tasks."""
        tasks = self.async_executor.list_tasks()

        if not tasks:
            print("\nNo background tasks.\n")
            return

        stats = self.async_executor.get_stats()

        print("\n" + "="*60)
        print("BACKGROUND TASKS")
        print("="*60)
        print(f"Total: {stats['total_tasks']} | Running: {stats['running']} | "
              f"Completed: {stats['completed']} | Failed: {stats['failed']}")
        print("="*60)

        for task in tasks:
            status_icon = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✓",
                "failed": "✗",
                "cancelled": "⊘"
            }.get(task['status'], "?")

            duration = task.get('duration')
            duration_str = f"{duration:.1f}s" if duration else "N/A"

            print(f"\n{status_icon} {task['id']}")
            print(f"  Status: {task['status'].upper()}")
            print(f"  Goal: {task['goal']}")
            print(f"  Duration: {duration_str}")
            if task.get('start_time'):
                print(f"  Started: {task['start_time']}")

        print("="*60 + "\n")

    def handle_task(self, args):
        """Check status of a specific task."""
        if not args:
            print("Error: Please provide a task ID")
            print("Example: /task task_1_1234567890\n")
            return

        task_id = " ".join(args)
        task = self.async_executor.get_task(task_id)

        if not task:
            print(f"\nTask not found: {task_id}\n")
            return

        status_icon = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✓",
            "failed": "✗",
            "cancelled": "⊘"
        }.get(task.status.value, "?")

        print("\n" + "="*60)
        print(f"TASK DETAILS: {task_id}")
        print("="*60)
        print(f"Status: {status_icon} {task.status.value.upper()}")
        print(f"Goal: {task.goal}")

        duration = task.get_duration()
        if duration:
            print(f"Duration: {duration:.1f}s")

        if task.start_time:
            print(f"Started: {task.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if task.end_time:
            print(f"Ended: {task.end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if task.error:
            print(f"\nError: {task.error}")

        # Get and display output
        output = task.get_output()
        if output:
            print("\nOutput:")
            print("-" * 60)
            for line in output:
                print(line)

        print("="*60 + "\n")

    def handle_cancel(self, args):
        """Cancel a running background task."""
        if not args:
            print("Error: Please provide a task ID")
            print("Example: /cancel task_1_1234567890\n")
            return

        task_id = " ".join(args)

        if self.async_executor.cancel_task(task_id):
            print(f"\n✓ Task cancelled: {task_id}\n")
        else:
            print(f"\n✗ Could not cancel task: {task_id}")
            print("Task may not exist or is already finished.\n")

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
        self.agent = AutonomousAgent(config=self.config)
        print("\nAgent reset. Conversation history cleared.\n")

    def handle_save(self, args):
        """Save current session."""
        if not self.agent.memory:
            print("\nMemory is disabled in configuration.\n")
            return

        session_name = " ".join(args) if args else None
        session_id = self.agent.memory.save_conversation(
            self.agent.conversation_history,
            session_name
        )

        if session_id:
            print(f"\nSession saved: {session_id}\n")
        else:
            print("\nNo conversation to save.\n")

    def handle_load(self, args):
        """Load a saved session."""
        if not self.agent.memory:
            print("\nMemory is disabled in configuration.\n")
            return

        session_id = " ".join(args) if args else None
        conversation = self.agent.memory.load_conversation(session_id)

        if conversation:
            self.agent.conversation_history = conversation
            print(f"\nLoaded session with {len(conversation)} messages.\n")
        else:
            print("\nNo session found.\n")

    def handle_sessions(self, args):
        """List all saved sessions."""
        if not self.agent.memory:
            print("\nMemory is disabled in configuration.\n")
            return

        sessions = self.agent.memory.list_sessions()

        if not sessions:
            print("\nNo saved sessions.\n")
            return

        print("\n" + "="*60)
        print("SAVED SESSIONS")
        print("="*60)
        for session in sessions:
            print(f"\nID: {session['id']}")
            print(f"Name: {session['name']}")
            print(f"Messages: {session['message_count']}")
            print(f"Time: {session['timestamp']}")
        print("="*60 + "\n")

    def handle_config(self, args):
        """Show configuration."""
        config = self.config.get_all()
        print("\n" + "="*60)
        print("CONFIGURATION")
        print("="*60)
        print(json.dumps(config, indent=2))
        print("="*60 + "\n")

    def handle_cost(self, args):
        """Show detailed cost report."""
        # Check if user wants detailed view
        show_details = "detail" in args or "details" in args or "-d" in args

        report = self.agent.cost_tracker.format_cost_report(include_details=show_details)
        print(f"\n{report}\n")

    def handle_exit(self, args):
        """Exit the terminal."""
        # Auto-save conversation before exit
        if self.agent.memory and self.config.get("memory.auto_save", True):
            if self.agent.conversation_history:
                self.agent.memory.save_conversation(
                    self.agent.conversation_history,
                    "auto-save"
                )

        # Save cost data
        self.agent.cost_tracker.save_session_costs()

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
                elif command == "/submit":
                    self.handle_submit(args)
                elif command == "/tasks":
                    self.handle_tasks(args)
                elif command == "/task":
                    self.handle_task(args)
                elif command == "/cancel":
                    self.handle_cancel(args)
                elif command == "/clear":
                    self.handle_clear(args)
                elif command == "/history":
                    self.handle_history(args)
                elif command == "/reset":
                    self.handle_reset(args)
                elif command == "/save":
                    self.handle_save(args)
                elif command == "/load":
                    self.handle_load(args)
                elif command == "/sessions":
                    self.handle_sessions(args)
                elif command == "/config":
                    self.handle_config(args)
                elif command == "/cost":
                    self.handle_cost(args)
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
