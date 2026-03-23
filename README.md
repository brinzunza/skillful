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

Run the agent with a goal:
```bash
python agent.py "your goal here"
```

### Examples

```bash
# Create a file
python agent.py "create a file called hello.txt with the content 'Hello World'"

# List and read files
python agent.py "list all files in the current directory and read the contents of README.md"

# Run shell commands
python agent.py "create a directory called test_dir and create 3 empty files in it"

# Complex tasks
python agent.py "find all .py files in the current directory and count the total lines of code"
```

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
- `run_shell_command` - Execute shell commands
- `create_directory` - Create directories
- `delete_file` - Delete files
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

## Safety

The agent can execute shell commands and modify your filesystem. Use with caution:

- Start with simple, safe goals
- The agent has access to your entire filesystem
- Shell commands run with your user permissions
- Review skills in `skills.py` before running

## License

MIT
