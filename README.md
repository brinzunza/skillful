# Skillful

A barebones autonomous AI agent that executes tasks on your machine using OpenAI's API.

## Features

- **🤖 Autonomous Execution** - Agent loops until task completion
- **💬 Interactive Terminal** - Command-line interface with real-time streaming
- **💾 Persistent Memory** - Save and resume conversation sessions
- **💰 Cost Tracking** - Real-time OpenAI API cost monitoring
- **🔒 Safety First** - Sandboxed to current directory with multiple safety layers
- **⚙️ Configurable** - YAML configuration for all settings

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=your-key-here
```

### 3. Run

```bash
python agent.py
```

You'll see:

```
============================================================
  SKILLFUL - Autonomous Agent Terminal
============================================================
Type /help for available commands
Type /exit to quit
============================================================

skillful>
```

## Usage

### Give the Agent Tasks

```bash
skillful> /order create a Python script that sorts a list

============================================================
ITERATION 1/20
============================================================

============================================================
AGENT REASONING (streaming...)
============================================================
I need to create a Python file with a sorting function...
[reasoning streams in real-time]
============================================================

[Executing: write_file]
Arguments: {
  "filepath": "sort_list.py",
  "content": "def sort_list(items):\n    return sorted(items)"
}

[Result]
Successfully wrote to sort_list.py

============================================================
GOAL ACHIEVED!
============================================================
```

### Commands

| Command | Description |
|---------|-------------|
| `/order <task>` | Give agent a task to complete |
| `/skills` | List all available skills |
| `/save [name]` | Save current session |
| `/load [id]` | Load a saved session |
| `/sessions` | List all saved sessions |
| `/cost` | Show cost report |
| `/config` | Show configuration |
| `/history` | Show conversation history |
| `/reset` | Reset agent |
| `/clear` | Clear screen |
| `/help` | Show help |
| `/exit` | Exit |

## How It Works

The agent operates in a simple loop:

1. **Think** - LLM decides what skill to use (streams reasoning in real-time)
2. **Act** - Execute the chosen skill
3. **Observe** - Get the result
4. **Repeat** - Continue until goal achieved

### Real-Time Streaming

Watch the agent think as responses stream live:

```
============================================================
AGENT REASONING (streaming...)
============================================================
I'll analyze the requirements and break this down into steps.
First, I need to... [streams character by character]
```

## Available Skills

The agent can:

- `read_file` - Read file contents
- `write_file` - Write to a file
- `edit_file` - Edit specific parts of a file (find and replace)
- `delete_file` - Delete files (requires confirmation)
- `list_directory` - List files in a directory
- `create_directory` - Create directories
- `run_shell_command` - Execute shell commands (safety-checked)
- `get_current_directory` - Get current working directory

## Key Features

### 1. Persistent Memory

Save and resume conversations:

```bash
# Save your work
skillful> /save my-project

# Later, resume where you left off
skillful> /load my-project
```

Sessions stored in `.skillful/sessions.json` with full conversation history.

### 2. Cost Tracking

Always know what you're spending:

```
============================================================
COST SUMMARY
============================================================
API Requests: 5
Total Tokens: 3,247
  Input:  2,156 tokens
  Output: 1,091 tokens
Session Cost: $0.0132
============================================================
```

View detailed breakdown:
```bash
skillful> /cost details
```

Lifetime costs tracked in `.skillful/costs.json`.

### 3. Configuration

Edit `.skillful/config.yaml`:

```yaml
model: gpt-4o-mini          # Model to use
max_iterations: 20           # Max loops
temperature: 0.7             # Creativity (0.0-2.0)

safety:
  enabled: true              # Safety checks
  max_high_risk_operations: 10

memory:
  enabled: true              # Persistent sessions
  auto_save: true            # Save on exit
```

## Safety Features

Multiple layers of protection:

### 1. Sandboxing
- **Agent cannot access parent directories** (`../` blocked)
- **Locked to current directory and subdirectories only**
- Home directory and system paths blocked

### 2. Dangerous Command Blocking
Automatically blocks:
- `rm -rf /`, `shutdown`, `reboot`
- Fork bombs, disk wipes
- Privilege escalation attempts

### 3. Protected Paths
System directories off-limits:
- `/bin`, `/etc`, `/usr`, etc.
- `~/.ssh`, `~/.bashrc`, `.env`

### 4. User Confirmation
File deletions require your approval:
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

### 5. Risk Monitoring
- Tracks operation risk levels
- Limits high-risk operations (max 10/session)
- Shows safety report after completion

## Adding Custom Skills

1. Open `skills.py`
2. Add your function:

```python
def my_skill(param: str) -> str:
    """
    Description of what this does.

    Args:
        param: Description

    Returns:
        Result description
    """
    # Your code here
    return "result"
```

3. Register it:

```python
SKILLS = {
    # ... existing skills ...
    "my_skill": my_skill,
}
```

The agent automatically discovers and uses new skills.

## Cost Control

### Tips to Save Money

1. **Use cheaper models:**
   ```yaml
   model: gpt-4o-mini  # $0.15 per 1M input tokens
   ```

2. **Reduce iterations:**
   ```yaml
   max_iterations: 10
   ```

3. **Clear context regularly:**
   ```bash
   skillful> /reset  # Clears conversation history
   ```

4. **Monitor spending:**
   ```bash
   skillful> /cost
   ```

### Pricing (2025)

| Model | Input | Output |
|-------|-------|--------|
| gpt-4o-mini | $0.15/1M | $0.60/1M |
| gpt-4o | $2.50/1M | $10.00/1M |
| gpt-4-turbo | $10.00/1M | $30.00/1M |

## File Structure

```
skillful/
├── agent.py              # Main agent
├── skills.py             # Skill definitions
├── safety.py             # Safety checks
├── memory.py             # Session management
├── config.py             # Configuration system
├── cost_tracker.py       # Cost tracking
├── async_executor.py     # Background tasks (experimental)
├── requirements.txt      # Dependencies
├── .env                  # Your API key (create this)
└── .skillful/            # Auto-created data directory
    ├── config.yaml       # Configuration
    ├── sessions.json     # Saved conversations
    └── costs.json        # Cost tracking data
```

## Troubleshooting

### "OPENAI_API_KEY not found"
Create `.env` file with your API key:
```bash
OPENAI_API_KEY=sk-your-key-here
```

### Permission errors
Agent can only access files in current directory. If you need to work elsewhere:
```bash
cd /path/to/your/project
python /path/to/skillful/agent.py
```

### High costs
Check your model setting in `.skillful/config.yaml` and use `gpt-4o-mini` for cheaper operations.

## Dependencies

- Python 3.7+
- openai >= 1.0.0
- python-dotenv >= 1.0.0
- pyyaml >= 6.0.0

## Security Notes

- Agent runs with your user permissions (not root)
- Cannot escape current directory sandbox
- All commands safety-checked before execution
- User confirmation required for deletions

### ⚠️ Sensitive Data

**IMPORTANT:** The following files contain sensitive information and are automatically excluded from git:

- `.env` - Your OpenAI API key
- `.skillful/sessions.json` - Full conversation history (may contain passwords, code, personal data)
- `.skillful/costs.json` - Your API usage and spending data
- `.skillful/config.yaml` - Your personal configuration

**Never commit these files to version control or share them publicly!**

These files are already in `.gitignore` and won't be committed by default.

## License

MIT

## Credits

Built with:
- OpenAI API for LLM capabilities
- Python for everything else
