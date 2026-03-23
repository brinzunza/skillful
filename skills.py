"""
Skills that the agent can use to interact with the system.
Each skill is a Python function with a docstring that describes what it does.
"""

import os
import subprocess
import json


def read_file(filepath: str) -> str:
    """
    Read the contents of a file.

    Args:
        filepath: Path to the file to read

    Returns:
        The contents of the file as a string
    """
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_file(filepath: str, content: str) -> str:
    """
    Write content to a file. Creates the file if it doesn't exist.

    Args:
        filepath: Path to the file to write
        content: Content to write to the file

    Returns:
        Success or error message
    """
    try:
        with open(filepath, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def list_directory(path: str = ".") -> str:
    """
    List files and directories in the given path.

    Args:
        path: Directory path to list (defaults to current directory)

    Returns:
        List of files and directories
    """
    try:
        items = os.listdir(path)
        return "\n".join(items)
    except Exception as e:
        return f"Error listing directory: {str(e)}"


def run_shell_command(command: str) -> str:
    """
    Execute a shell command and return its output.

    Args:
        command: Shell command to execute

    Returns:
        Command output or error message
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout if result.stdout else result.stderr
        return output if output else "Command executed successfully (no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


def create_directory(path: str) -> str:
    """
    Create a new directory.

    Args:
        path: Path of the directory to create

    Returns:
        Success or error message
    """
    try:
        os.makedirs(path, exist_ok=True)
        return f"Successfully created directory: {path}"
    except Exception as e:
        return f"Error creating directory: {str(e)}"


def delete_file(filepath: str) -> str:
    """
    Delete a file.

    Args:
        filepath: Path to the file to delete

    Returns:
        Success or error message
    """
    try:
        os.remove(filepath)
        return f"Successfully deleted {filepath}"
    except Exception as e:
        return f"Error deleting file: {str(e)}"


def get_current_directory() -> str:
    """
    Get the current working directory.

    Returns:
        The current working directory path
    """
    return os.getcwd()


# Registry of all available skills
SKILLS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "run_shell_command": run_shell_command,
    "create_directory": create_directory,
    "delete_file": delete_file,
    "get_current_directory": get_current_directory,
}


def get_skills_description() -> str:
    """
    Generate a description of all available skills for the LLM.

    Returns:
        JSON string describing all skills and their parameters
    """
    skills_info = []
    for name, func in SKILLS.items():
        # Parse docstring and function signature
        doc = func.__doc__.strip() if func.__doc__ else "No description"

        # Get function parameters
        import inspect
        sig = inspect.signature(func)
        params = {}
        for param_name, param in sig.parameters.items():
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else "any"
            param_default = param.default if param.default != inspect.Parameter.empty else None
            params[param_name] = {
                "type": str(param_type),
                "required": param.default == inspect.Parameter.empty
            }

        skills_info.append({
            "name": name,
            "description": doc,
            "parameters": params
        })

    return json.dumps(skills_info, indent=2)


def execute_skill(skill_name: str, **kwargs) -> str:
    """
    Execute a skill by name with given arguments.

    Args:
        skill_name: Name of the skill to execute
        **kwargs: Arguments to pass to the skill

    Returns:
        Result from the skill execution
    """
    if skill_name not in SKILLS:
        return f"Error: Skill '{skill_name}' not found"

    try:
        result = SKILLS[skill_name](**kwargs)
        return str(result)
    except Exception as e:
        return f"Error executing skill '{skill_name}': {str(e)}"
