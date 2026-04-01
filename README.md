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
2. **Think**: Uses OpenAI to decide what skill to use next
3. **Act**: Executes the chosen skill with the provided arguments
4. **Observe**: Gets the result and feeds it back to the LLM
5. **Repeat**: Continues until the goal is achieved or max iterations reached

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

Edit `agent.py` to customize:

- `model` - Change the OpenAI model (default: `gpt-4o-mini`)
- `max_iterations` - Maximum loops before stopping (default: 20)
- `temperature` - LLM creativity (default: 0.7)

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
