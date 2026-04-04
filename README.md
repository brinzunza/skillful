# Skillful - Autonomous Agent

A super simple, barebones autonomous agent that can execute skills to achieve goals on your machine.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root:
```bash
cp .env.example .env
```

3. Add your OpenAI API key to the `.env` file:
```
OPENAI_API_KEY=your-api-key-here
```

## Usage

### Interactive Terminal Mode (Recommended)

Run Skillful without arguments to enter interactive terminal mode:

```bash
python agent.py
```

You'll see a terminal prompt:

```
============================================================
  SKILLFUL - Autonomous Agent Terminal
============================================================
Type /help for available commands
Type /exit to quit
============================================================

skillful> _
```

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/order <task>` | Give the agent a task to complete | `/order create a file called hello.txt` |
| `/skills` | List all available skills | `/skills` |
| `/help` | Show help message | `/help` |
| `/clear` | Clear the screen | `/clear` |
| `/history` | Show last 10 conversation entries | `/history` |
| `/reset` | Reset agent (clear history) | `/reset` |
| `/save [name]` | Save current session to memory | `/save my-session` |
| `/load [id]` | Load a saved session | `/load 20260403_143022` |
| `/sessions` | List all saved sessions | `/sessions` |
| `/undo` | Undo last operation (git rollback) | `/undo` |
| `/status` | Show git status | `/status` |
| `/config` | Show current configuration | `/config` |
| `/cost` | Show cost report | `/cost` or `/cost details` |
| `/exit` | Exit the terminal | `/exit` |

### Example Session

```bash
skillful> /order create a file called hello.txt with Hello World

Executing task: create a file called hello.txt with Hello World

============================================================
GOAL: create a file called hello.txt with Hello World
============================================================

--- Iteration 1 ---
Reasoning: I need to write content to a new file...
Action: execute
Executing: write_file({'filepath': 'hello.txt', 'content': 'Hello World'})
Result: Successfully wrote to hello.txt...

============================================================
GOAL ACHIEVED!
============================================================

skillful> /skills

============================================================
AVAILABLE SKILLS
============================================================
• read_file
  Read the contents of a file.
• write_file
  Write content to a file. Creates the file if it doesn't exist.
...

skillful> /exit

Goodbye!
```

### Single Command Mode (Legacy)

You can also run tasks directly from the command line:

```bash
python agent.py "create a file called test.txt"
```

This is useful for scripting or one-off tasks.

## How It Works

1. **Agent Loop**: The agent runs in a loop (think → act → observe → repeat)
2. **Think**: Uses OpenAI to decide what skill to use next (streams reasoning in real-time)
3. **Act**: Executes the chosen skill with the provided arguments
4. **Observe**: Gets the result and feeds it back to the LLM
5. **Repeat**: Continues until the goal is achieved or max iterations reached

### Real-Time Streaming

The agent streams LLM responses in real-time, so you can see the reasoning as it's generated:

```
============================================================
ITERATION 1/20
============================================================

============================================================
AGENT REASONING (streaming...)
============================================================
I need to create a new file called hello.txt. The best approach
is to use the write_file skill with the filepath and content
parameters. This will create the file if it doesn't exist.

[JSON Response]
============================================================

[Executing: write_file]
Arguments: {
  "filepath": "hello.txt",
  "content": "Hello World"
}

[Result]
Successfully wrote to hello.txt
```

This provides immediate feedback and makes the agent's decision-making process transparent.

## Available Skills

The agent has access to these built-in skills (defined in `skills.py`):

- `read_file` - Read file contents
- `write_file` - Write to a file
- `list_directory` - List files in a directory
- `run_shell_command` - Execute shell commands (safety-checked)
- `create_directory` - Create directories
- `delete_file` - Delete files **[REQUIRES USER CONFIRMATION]**
- `get_current_directory` - Get current working directory

## Adding Custom Skills

To add a new skill:

1. Open `skills.py`
2. Add a new function with a descriptive docstring:

```python
def my_custom_skill(param1: str, param2: int) -> str:
    """
    Description of what this skill does.

    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2

    Returns:
        Description of what is returned
    """
    # Your implementation here
    return "result"
```

3. Add it to the `SKILLS` registry:

```python
SKILLS = {
    # ... existing skills ...
    "my_custom_skill": my_custom_skill,
}
```

The agent will automatically discover and use new skills.

## Configuration

Skillful uses a YAML configuration file at `.skillful/config.yaml`. The file is auto-created with defaults on first run.

### Configuration Options

```yaml
model: gpt-4o-mini          # OpenAI model to use
max_iterations: 20           # Max agent loop iterations
temperature: 0.7             # LLM creativity (0.0-2.0)

safety:
  enabled: true              # Enable safety checks
  max_high_risk_operations: 10  # Max high-risk ops per session
  require_confirmation:      # Skills requiring user confirmation
    - delete_file

memory:
  enabled: true              # Enable persistent memory
  auto_save: true            # Auto-save on exit

async:
  enabled: false             # Enable async task execution
  max_concurrent_tasks: 1    # Max concurrent tasks

undo:
  enabled: true              # Enable undo/rollback
  use_git: true              # Use git for undo
  auto_commit: true          # Auto-commit before operations
```

### Viewing Configuration

```bash
skillful> /config
```

### Editing Configuration

Edit `.skillful/config.yaml` directly, then restart the agent or use `/reset`.

## Persistent Memory

Skillful can save and load conversation sessions, allowing you to resume work later or maintain context across restarts.

### Saving Sessions

```bash
# Save current session with a name
skillful> /save my-important-work

# Auto-saves on exit (if memory.auto_save: true)
skillful> /exit
```

### Loading Sessions

```bash
# Load most recent session
skillful> /load

# Load specific session by ID
skillful> /load 20260403_143022_my-important-work
```

### Managing Sessions

```bash
# List all saved sessions
skillful> /sessions

SAVED SESSIONS
============================================================

ID: 20260403_143022_my-important-work
Name: my-important-work
Messages: 24
Time: 2026-04-03T14:30:22

...
```

### How It Works

- Sessions are stored in `.skillful/sessions.json`
- Each session includes full conversation history
- Load a session to continue where you left off
- Agent has context of previous interactions

## Undo/Rollback (Git Integration)

Skillful uses git to create automatic checkpoints before risky operations, allowing you to undo mistakes.

### Automatic Checkpoints

The agent automatically creates git commits before:
- Writing files (`write_file`)
- Deleting files (`delete_file`)
- Running shell commands (`run_shell_command`)

### Undoing Operations

```bash
# Undo the last operation
skillful> /undo

Undone: write_file {'filepath': 'test.txt', 'content': '...'}

# Check git status
skillful> /status

Git Status:
 M test.txt
```

### How It Works

- Git repo is auto-initialized if it doesn't exist
- Each risky operation creates a commit
- `/undo` rolls back to the previous commit
- Stack-based: can undo multiple operations in order
- `.skillful/` directory is automatically gitignored

### Requirements

- Git must be installed on your system
- Agent must have write permissions in the directory

### Disabling Undo

Set in `.skillful/config.yaml`:
```yaml
undo:
  enabled: false
```

## Cost Tracking

Skillful automatically tracks OpenAI API costs for every request, giving you visibility into spending.

### Automatic Tracking

Every LLM request is tracked with:
- Input tokens (prompt)
- Output tokens (completion)
- Cost per request
- Model used

### Viewing Costs

```bash
# Quick summary (shown after each task)
============================================================
COST SUMMARY
============================================================
API Requests: 5
Total Tokens: 3,247
  Input:  2,156 tokens
  Output: 1,091 tokens
Session Cost: $0.0132
============================================================

# Detailed report
skillful> /cost

============================================================
COST REPORT - Current Session
============================================================
Total Requests: 5
Total Tokens: 3,247
  Input:  2,156 tokens
  Output: 1,091 tokens
Total Cost: $0.0132
Average Cost per Request: $0.0026

HISTORICAL SUMMARY
============================================================
Total Sessions: 12
Lifetime Cost: $0.47
Lifetime Tokens: 124,583
Average per Session: $0.0392
============================================================

# Per-request details
skillful> /cost details
...
Request 1:
  Model: gpt-4o-mini
  Tokens: 1,245 (834 in + 411 out)
  Cost: $0.0037
...
```

### How It Works

- **Real-time tracking**: Costs calculated immediately after each API call
- **Persistent storage**: Session costs saved to `.skillful/costs.json`
- **Historical data**: Lifetime stats across all sessions
- **Accurate pricing**: Uses official OpenAI pricing (updated for 2024-2025)

### Pricing (as of 2025)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4-turbo | $10.00 | $30.00 |
| gpt-3.5-turbo | $0.50 | $1.50 |

### Controlling Costs

1. **Use cheaper models** - Edit `.skillful/config.yaml`:
   ```yaml
   model: gpt-4o-mini  # Cheapest option
   ```

2. **Limit iterations** - Reduce max loop count:
   ```yaml
   max_iterations: 10  # Default: 20
   ```

3. **Monitor spending** - Check `/cost` regularly

4. **Clear history** - Conversation history increases token usage:
   ```bash
   skillful> /reset  # Clears context, reduces future costs
   ```

### Cost Data

All cost data stored in `.skillful/costs.json`:
- Survives restarts
- Per-session breakdowns
- Full request history

## Async Execution (Coming Soon)

Background task execution is implemented but disabled by default. This feature allows running multiple agent tasks concurrently.

To enable (experimental):
```yaml
async:
  enabled: true
  max_concurrent_tasks: 3
```

## Safety Features

The agent includes built-in safety mechanisms to prevent catastrophic failures:

### Automatic Protections

1. **Working Directory Restriction** (Sandbox)
   - **Agent can ONLY access files in current directory and subdirectories**
   - Parent directory access is blocked (e.g., `../file.txt` is denied)
   - Absolute paths outside working directory are blocked
   - Home directory paths (`~/.bashrc`) are blocked
   - This creates a sandbox - the agent cannot escape the project folder

2. **Command Validation**
   - Blocks dangerous shell commands (rm -rf /, fork bombs, etc.)
   - Prevents system modification commands (shutdown, reboot, etc.)
   - Detects suspicious command patterns and obfuscation

3. **Protected Paths**
   - System directories are off-limits (`/bin`, `/etc`, `/usr`, etc.)
   - Critical config files protected (`~/.ssh`, `~/.bashrc`, `.env`, etc.)
   - Won't delete or modify important project files

4. **User Confirmation for Deletions**
   - **All file deletions require explicit user approval**
   - Agent pauses and prompts you before deleting any file
   - You can approve (yes) or deny (no) each deletion
   - Example prompt:
   ```
   ============================================================
   CONFIRMATION REQUIRED
   ============================================================
   Skill: delete_file
   Arguments: {
     "filepath": "important.txt"
   }
   ============================================================
   Allow this operation? (yes/no):
   ```

5. **Risk Monitoring**
   - Tracks risk level of each operation (low/medium/high/critical)
   - Blocks critical operations automatically
   - Limits high-risk operations (max 10 per session)
   - Prints safety report at end of execution

### Safety Report

After each run, you'll see a safety report:
```
SAFETY REPORT
============================================================
Total operations: 5
Blocked operations: 1

Risk distribution:
  LOW: 2
  MEDIUM: 2
  HIGH: 1

Blocked operations:
  - Shell command blocked: rm -rf /
============================================================
```

### Disabling Safety (Not Recommended)

If you need to disable safety checks for testing:

```python
# In agent.py main()
agent = AutonomousAgent(enable_safety=False)
```

**Warning**: Only disable safety in controlled environments! User confirmation for deletions will still be required.

### What Gets Blocked

- **Parent directory access**: `../file.txt`, `../../config`, etc.
- **Paths outside working directory**: `/tmp/test.txt`, `~/file.txt`, `/etc/passwd`
- Destructive commands: `rm -rf /`, `dd if=...`, `mkfs`, fork bombs
- System commands: `shutdown`, `reboot`, `halt`
- Privilege escalation: `sudo rm`, `chmod 777 /`
- Protected file operations on system/config files
- Excessive command chaining or substitution (potential obfuscation)

## Usage Notes

- **The agent operates in a sandbox** - it can only access the current directory and subdirectories
- Start with simple, safe goals to test behavior
- Review the safety report after each run
- **You'll be prompted to confirm any file deletions**
- Shell commands run with your user permissions (not root)

## License

MIT
