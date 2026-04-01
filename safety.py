"""
Safety and security features to prevent catastrophic commands.
"""

import re
import os
from typing import Tuple, List
from pathlib import Path


class SafetyError(Exception):
    """Raised when a dangerous operation is blocked."""
    pass


# Dangerous shell command patterns
DANGEROUS_PATTERNS = [
    # Destructive commands
    r'\brm\s+-rf\s+/',  # rm -rf /
    r'\brm\s+-rf\s+~',  # rm -rf ~
    r'\brm\s+-rf\s+\*',  # rm -rf *
    r'\bdd\s+if=.*of=/dev/sd',  # disk wipe
    r':\(\)\{.*\}',  # fork bomb
    r'mkfs\.',  # format filesystem

    # System modification
    r'\bshutdown\b',
    r'\breboot\b',
    r'\bhalt\b',
    r'\bpoweroff\b',
    r'\bkillall\b',

    # Network attacks
    r'\bnmap\b.*-sS',  # SYN scan
    r'\bhping\b',
    r'\bddos\b',

    # Privilege escalation
    r'\bsudo\s+rm\b',
    r'\bsudo\s+dd\b',
    r'\bchmod\s+777\s+/',

    # Package manager dangers
    r'\bapt-get\s+remove\s+--purge',
    r'\byum\s+remove',
    r'\bpip\s+uninstall.*-y',
]

# Protected paths that should never be modified
PROTECTED_PATHS = [
    '/',
    '/bin',
    '/sbin',
    '/boot',
    '/dev',
    '/etc',
    '/lib',
    '/lib64',
    '/proc',
    '/root',
    '/sys',
    '/usr',
    '/var/log',
    os.path.expanduser('~/.ssh'),
    os.path.expanduser('~/.bash_profile'),
    os.path.expanduser('~/.bashrc'),
    os.path.expanduser('~/.zshrc'),
]

# File extensions that are risky to delete
PROTECTED_EXTENSIONS = [
    '.git',
    '.env',
    '.ssh',
]


def is_within_working_directory(path: str) -> bool:
    """
    Check if a path is within or below the current working directory.
    Prevents access to parent directories.

    Args:
        path: Path to check

    Returns:
        True if path is within or below cwd, False otherwise
    """
    try:
        # Expand user paths (~ to home directory)
        expanded_path = os.path.expanduser(path)

        # Get absolute paths
        cwd = Path.cwd().resolve()
        target = Path(expanded_path).resolve()

        # Check if target is cwd or a subdirectory
        # This works by checking if cwd is a parent of target (or equal to it)
        try:
            target.relative_to(cwd)
            return True
        except ValueError:
            # relative_to raises ValueError if target is not relative to cwd
            return False
    except Exception:
        # If there's any error resolving paths, deny access
        return False


def is_protected_path(path: str) -> bool:
    """
    Check if a path is protected from modification.

    Args:
        path: Path to check

    Returns:
        True if path is protected
    """
    # Normalize the path
    abs_path = os.path.abspath(os.path.expanduser(path))

    # Check if it matches any protected path
    for protected in PROTECTED_PATHS:
        protected_abs = os.path.abspath(os.path.expanduser(protected))
        if abs_path == protected_abs or abs_path.startswith(protected_abs + os.sep):
            return True

    # Check for protected extensions
    for ext in PROTECTED_EXTENSIONS:
        if path.endswith(ext) or f'/{ext}/' in path:
            return True

    return False


def validate_shell_command(command: str) -> Tuple[bool, str]:
    """
    Validate a shell command for dangerous patterns.

    Args:
        command: Shell command to validate

    Returns:
        Tuple of (is_safe, reason)
    """
    # Check against dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"Blocked: Command matches dangerous pattern '{pattern}'"

    # Check for suspicious pipe chains that could hide dangerous commands
    if command.count('|') > 3:
        return False, "Blocked: Too many pipes in command (potential obfuscation)"

    # Check for command substitution abuse
    if command.count('$(') > 2 or command.count('`') > 2:
        return False, "Blocked: Excessive command substitution detected"

    return True, "Command appears safe"


def validate_file_operation(operation: str, filepath: str) -> Tuple[bool, str]:
    """
    Validate file operations for safety.

    Args:
        operation: Type of operation ('write', 'delete', 'create')
        filepath: Path to the file

    Returns:
        Tuple of (is_safe, reason)
    """
    # First check: Must be within working directory
    if not is_within_working_directory(filepath):
        return False, f"Blocked: Path '{filepath}' is outside the working directory. Agent can only access current directory and subdirectories."

    # Check if path is protected
    if is_protected_path(filepath):
        return False, f"Blocked: Path '{filepath}' is protected"

    # Additional checks for delete operations
    if operation == 'delete':
        # Don't allow deleting entire directories
        if os.path.isdir(filepath):
            return False, "Blocked: Cannot delete directories (use with caution)"

        # Warn about deleting important files
        important_files = ['.env', 'requirements.txt', 'config.json', 'package.json']
        if os.path.basename(filepath) in important_files:
            return False, f"Blocked: '{filepath}' is a critical file"

    return True, "File operation appears safe"


def needs_user_confirmation(skill_name: str, args: dict) -> bool:
    """
    Check if a skill requires user confirmation before execution.

    Args:
        skill_name: Name of the skill
        args: Arguments being passed to the skill

    Returns:
        True if user confirmation is required
    """
    # File deletion always requires confirmation
    if skill_name == 'delete_file':
        return True

    return False


def assess_risk_level(skill_name: str, args: dict) -> str:
    """
    Assess the risk level of a skill execution.

    Args:
        skill_name: Name of the skill
        args: Arguments being passed to the skill

    Returns:
        Risk level: 'low', 'medium', 'high', 'critical'
    """
    # Critical risk operations
    if skill_name == 'run_shell_command':
        command = args.get('command', '')
        is_safe, _ = validate_shell_command(command)
        if not is_safe:
            return 'critical'

        # Medium risk for any shell command
        return 'medium'

    if skill_name == 'delete_file':
        return 'high'

    if skill_name == 'write_file':
        filepath = args.get('filepath', '')
        if is_protected_path(filepath):
            return 'critical'
        return 'medium'

    # Low risk operations
    if skill_name in ['read_file', 'list_directory', 'get_current_directory']:
        return 'low'

    return 'medium'


class SafetyMonitor:
    """Monitor and track safety violations during agent execution."""

    def __init__(self, max_high_risk_operations: int = 10):
        """
        Initialize the safety monitor.

        Args:
            max_high_risk_operations: Maximum number of high-risk ops before blocking
        """
        self.violations = []
        self.high_risk_count = 0
        self.max_high_risk_operations = max_high_risk_operations
        self.operation_history = []

    def check_operation(self, skill_name: str, args: dict) -> Tuple[bool, str]:
        """
        Check if an operation should be allowed.

        Args:
            skill_name: Name of the skill to execute
            args: Arguments for the skill

        Returns:
            Tuple of (is_allowed, reason)
        """
        # Assess risk level
        risk_level = assess_risk_level(skill_name, args)

        # Track operation
        self.operation_history.append({
            'skill': skill_name,
            'args': args,
            'risk': risk_level
        })

        # Block critical operations
        if risk_level == 'critical':
            self.violations.append(f"CRITICAL: {skill_name} with args {args}")
            return False, "CRITICAL RISK: Operation blocked for safety"

        # Track high-risk operations
        if risk_level in ['high', 'medium']:
            self.high_risk_count += 1

            # Block if too many high-risk operations
            if self.high_risk_count > self.max_high_risk_operations:
                return False, f"Too many high-risk operations ({self.high_risk_count}). Agent halted for safety."

        # Additional validation for specific skills
        if skill_name == 'run_shell_command':
            command = args.get('command', '')
            is_safe, reason = validate_shell_command(command)
            if not is_safe:
                self.violations.append(f"Shell command blocked: {command}")
                return False, reason

        if skill_name in ['write_file', 'delete_file']:
            filepath = args.get('filepath', '')
            operation = 'delete' if skill_name == 'delete_file' else 'write'
            is_safe, reason = validate_file_operation(operation, filepath)
            if not is_safe:
                self.violations.append(f"File operation blocked: {operation} on {filepath}")
                return False, reason

        return True, f"Operation allowed (risk: {risk_level})"

    def get_safety_report(self) -> dict:
        """
        Get a report of safety metrics.

        Returns:
            Dictionary with safety statistics
        """
        total_ops = len(self.operation_history)
        risk_counts = {
            'low': sum(1 for op in self.operation_history if op['risk'] == 'low'),
            'medium': sum(1 for op in self.operation_history if op['risk'] == 'medium'),
            'high': sum(1 for op in self.operation_history if op['risk'] == 'high'),
            'critical': sum(1 for op in self.operation_history if op['risk'] == 'critical'),
        }

        return {
            'total_operations': total_ops,
            'violations': len(self.violations),
            'risk_distribution': risk_counts,
            'violation_details': self.violations
        }
