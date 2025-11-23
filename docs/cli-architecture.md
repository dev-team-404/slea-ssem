# CLI Architecture Documentation

## Overview

This document describes the **Config-Driven, Dynamic Dispatcher CLI Architecture** implemented in `src/cli/`. This architecture provides a clean, maintainable, and extensible way to build interactive command-line interfaces with hierarchical command structures.

**Key Features:**
- **Config-driven**: All commands defined in a single dictionary (no hardcoded routing)
- **Dynamic loading**: Command handlers loaded at runtime using `importlib`
- **Hierarchical commands**: Multi-level sub-commands (e.g., `profile nickname check`)
- **Type-safe**: Pydantic validation for command configuration
- **Context-based DI**: Clean dependency injection via `CLIContext`
- **Rich UI**: Beautiful terminal output using Rich Console
- **Auto-completion**: Intelligent command completion using prompt_toolkit

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  User Input: "profile nickname check myname"                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  CLI (main.py)                                                   │
│  - PromptSession (prompt_toolkit)                                │
│  - WordCompleter (auto-completion)                               │
│  - Parse input → (command_path, args)                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  CLIDispatcher (main.py)                                         │
│  1. _get_command_target(command_path)                            │
│     → Traverse COMMAND_LAYOUT hierarchy                          │
│     → Return target: "src.cli.actions.profile.check_nickname"    │
│                                                                   │
│  2. _import_and_get_func(target_path)                            │
│     → importlib.import_module("src.cli.actions.profile")         │
│     → getattr(module, "check_nickname_availability")             │
│     → Return function object                                     │
│                                                                   │
│  3. func(context, *args)                                         │
│     → Execute with CLIContext + arguments                        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Action Function (actions/profile.py)                            │
│  def check_nickname_availability(context, *args):                │
│      - Access: context.console, context.logger                   │
│      - Call: context.client.make_request(...)                    │
│      - Update: context.session.token, etc.                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Command Configuration (`config/`)

#### `command_layout.py` - Command Definition Dictionary

All CLI commands are defined in a **single hierarchical dictionary**:

```python
COMMAND_LAYOUT = {
    "profile": {
        "description": "사용자 프로필 관리",
        "usage": "profile [subcommand]",
        "target": "src.cli.actions.profile.profile_help",  # Default handler
        "sub_commands": {
            "nickname": {
                "description": "닉네임 관련 명령어",
                "usage": "profile nickname [subcommand]",
                "target": "src.cli.actions.profile.profile_help",
                "sub_commands": {
                    "check": {
                        "description": "닉네임 중복 확인",
                        "usage": "profile nickname check [nickname]",
                        "target": "src.cli.actions.profile.check_nickname_availability",
                    },
                    "register": {
                        "description": "닉네임 등록",
                        "usage": "profile nickname register [nickname]",
                        "target": "src.cli.actions.profile.register_nickname",
                    }
                }
            }
        }
    },
    "auth": {
        "description": "인증 및 세션 관리",
        "usage": "auth [subcommand]",
        "target": "src.cli.actions.auth.auth_help",
        "sub_commands": {
            "login": {
                "description": "로그인",
                "usage": "auth login [username]",
                "target": "src.cli.actions.auth.login",
            }
        }
    },
    "help": {
        "description": "사용 가능한 명령어 목록",
        "usage": "help",
        "target": "src.cli.actions.system.help",
    }
}
```

**Key Fields:**
- `description`: Help text
- `usage`: Usage example (shown in help)
- `target`: Module path to handler function (`"module.path.function_name"`)
- `sub_commands`: Nested sub-commands (optional)

#### `models.py` - Pydantic Validation Models

```python
from pydantic import BaseModel, Field

class Command(BaseModel):
    """Represents a CLI command with optional sub-commands."""
    description: str = Field(..., description="명령어 설명")
    usage: str | None = Field(None, description="사용법 예시")
    target: str | None = Field(None, min_length=1, description="'module.function' 경로")
    sub_commands: dict[str, "Command"] | None = Field(None, description="하위 명령어")

class CommandConfig(BaseModel):
    """Top-level configuration model."""
    commands: dict[str, Command]
```

**Benefits:**
- Type safety at load time
- Automatic validation of command structure
- IDE autocomplete support

#### `loader.py` - Configuration Loader

```python
from src.cli.config.command_layout import COMMAND_LAYOUT
from src.cli.config.models import CommandConfig

def load_config() -> CommandConfig:
    """Load and validate command configuration."""
    return CommandConfig(commands=COMMAND_LAYOUT)
```

---

### 2. Context & Dependency Injection (`context.py`)

#### `CLIContext` - Dependency Injection Container

All CLI components share state through a single context object:

```python
from dataclasses import dataclass, field
from logging import Logger
from rich.console import Console
from src.cli.client import APIClient

@dataclass
class SessionState:
    """Session state managed by CLI."""
    token: str | None = None
    user_id: str | None = None
    username: str | None = None
    current_session_id: str | None = None
    current_round: int | None = None

@dataclass
class CLIContext:
    """Dependency injection container for CLI operations."""
    console: Console                                    # Rich console for output
    logger: Logger                                      # Logger instance
    client: APIClient = field(default_factory=lambda: APIClient())  # HTTP client
    session: SessionState = field(default_factory=SessionState)     # Session state
```

**Usage Pattern:**
```python
def my_action(context: CLIContext, *args: str) -> None:
    # Access dependencies
    context.console.print("[green]Success![/green]")
    context.logger.info("Action executed")

    # Make API calls
    status, response, error = context.client.make_request("GET", "/api/endpoint")

    # Update session state
    context.session.token = response["token"]
```

**Benefits:**
- **No global state**: All state passed explicitly
- **Easy testing**: Mock CLIContext in tests
- **Clean dependencies**: All dependencies visible in function signature

---

### 3. API Client (`client.py`)

HTTP client wrapper for FastAPI backend communication:

```python
import httpx

class APIClient:
    """HTTP client for communicating with FastAPI backend."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout)
        self.token: str | None = None

    def set_token(self, token: str) -> None:
        """Set JWT token for authenticated requests."""
        self.token = token

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with auth token if available."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def make_request(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
        params: dict | None = None,
    ) -> tuple[int, dict | None, str | None]:
        """
        Make HTTP request to API.

        Returns:
            (status_code, response_json, error_message)
            - Success: (200, {...}, None)
            - Error: (status_code, None, error_message)
        """
        try:
            response = self.client.request(
                method,
                path,
                headers=self._get_headers(),
                json=json_data,
                params=params,
            )

            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", response.text)
                except json.JSONDecodeError:
                    error_msg = response.text
                return response.status_code, None, error_msg

            return response.status_code, response.json(), None

        except httpx.ConnectError as e:
            return 0, None, f"Failed to connect: {str(e)}"
        except httpx.RequestError as e:
            return 0, None, f"Request failed: {str(e)}"
```

**Usage in Actions:**
```python
def login(context: CLIContext, *args: str) -> None:
    username = args[0]

    status_code, response, error = context.client.make_request(
        "POST",
        "/auth/login",
        json_data={"knox_id": username, "email": f"{username}@samsung.com"},
    )

    if error:
        context.console.print(f"[red]✗ Login failed: {error}[/red]")
        return

    token = response["access_token"]
    context.client.set_token(token)
    context.session.token = token
    context.console.print(f"[green]✓ Logged in as {username}[/green]")
```

---

### 4. Main CLI Loop (`main.py`)

#### `CLI` Class - Interactive Prompt Loop

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

class CLI:
    """Interactive CLI application using prompt_toolkit."""

    def __init__(self):
        self.console = Console()
        self.logger = logger
        self.context = CLIContext(console=self.console, logger=self.logger)
        self.command_config = load_config()
        self.dispatcher = CLIDispatcher(self.command_config, self.context)
        self.session = PromptSession(history=InMemoryHistory())
        self.should_exit = False
        atexit.register(self._cleanup)

    def _get_completer(self, current_commands: dict) -> WordCompleter:
        """Generate auto-completer for current command level."""
        words = list(current_commands.keys())
        return WordCompleter(words, ignore_case=True)

    def _parse_input(self, text: str) -> tuple[list[str], list[str]]:
        """
        Parse input into command path and arguments.

        Input: "profile nickname check myname"
        Output: (["profile", "nickname", "check"], ["myname"])
        """
        parts = shlex.split(text.strip())  # Handle quoted strings
        if not parts:
            return [], []

        command_path = []
        args = []
        current_level = self.command_config.commands

        for i, part in enumerate(parts):
            if part in current_level:
                command_path.append(part)
                if current_level[part].sub_commands:
                    current_level = current_level[part].sub_commands
                else:
                    args = parts[i + 1:]
                    break
            else:
                if not command_path:
                    command_path.append(part)  # For error message
                args = parts[i:]
                break

        return command_path, args

    def run(self):
        """Run interactive CLI main loop."""
        self.console.print("[green]Welcome to CLI![/green]")

        while True:
            try:
                if self.should_exit:
                    break

                completer = self._get_completer(self.command_config.commands)
                text = self.session.prompt("> ", completer=completer)

                command_path, args = self._parse_input(text)

                if not command_path:
                    continue

                if command_path[0] == "exit":
                    self.should_exit = True
                    break

                self.dispatcher.dispatch(command_path, args)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Ctrl-C to exit[/yellow]")
            except EOFError:
                self.should_exit = True
                break
```

#### `CLIDispatcher` Class - Dynamic Command Dispatcher

```python
import importlib

class CLIDispatcher:
    """Dispatcher for executing CLI commands based on configuration."""

    def __init__(self, command_config: CommandConfig, context: CLIContext):
        self.command_config = command_config
        self.context = context
        self.console = context.console
        self.logger = context.logger

    def _get_command_target(self, command_path: list[str]) -> str | None:
        """
        Find target function path for given command path.

        Example:
            Input: ["profile", "nickname", "check"]
            Output: "src.cli.actions.profile.check_nickname_availability"
        """
        current_level = self.command_config.commands
        target = None

        for i, cmd_name in enumerate(command_path):
            if cmd_name in current_level:
                cmd_obj = current_level[cmd_name]
                if i == len(command_path) - 1:  # Last command
                    target = cmd_obj.target
                if cmd_obj.sub_commands:
                    current_level = cmd_obj.sub_commands
                else:
                    break
            else:
                return None  # Command not found

        return target

    def _import_and_get_func(self, target_path: str) -> Callable | None:
        """
        Dynamically import and return function object.

        Example:
            Input: "src.cli.actions.profile.check_nickname_availability"
            Process:
                1. Split: module="src.cli.actions.profile", func="check_nickname_availability"
                2. import module
                3. getattr(module, func)
            Output: <function check_nickname_availability>
        """
        try:
            module_path, func_name = target_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            return func
        except (ImportError, AttributeError) as e:
            self.logger.error(f"Error loading command: {target_path} - {e}")
            self.console.print(f"[red]Error loading command: {target_path}[/red]")
            return None

    def dispatch(self, command_path: list[str], args: list[str]) -> None:
        """
        Execute command by:
        1. Finding target function path
        2. Dynamically importing function
        3. Calling function with context + args
        """
        if not command_path:
            return

        # Special handling for help/exit
        if command_path[0] in ("help", "exit"):
            target_path = self._get_command_target(["help"])
            if target_path:
                func = self._import_and_get_func(target_path)
                if func:
                    func(self.context, *args)
            return

        target_path = self._get_command_target(command_path)

        if target_path:
            func = self._import_and_get_func(target_path)
            if func:
                try:
                    # All action functions take (context, *args)
                    func(self.context, *args)
                except Exception as e:
                    self.logger.error(f"Error executing command: {e}", exc_info=True)
                    self.console.print(f"[red]Error: {e}[/red]")
            else:
                self.console.print(f"[red]Could not load command[/red]")
        else:
            self.console.print(f"[red]Unknown command: {' '.join(command_path)}[/red]")
            self.console.print("[yellow]Type 'help' for available commands[/yellow]")
```

---

### 5. Action Functions (`actions/`)

All command handlers follow a **consistent signature**:

```python
def action_name(context: CLIContext, *args: str) -> None:
    """Action description."""
    # 1. Validate arguments
    if not args:
        context.console.print("[yellow]Usage: command [arg1] [arg2][/yellow]")
        return

    # 2. Check authentication if needed
    if not context.session.token:
        context.console.print("[red]✗ Not authenticated[/red]")
        context.console.print("[yellow]Please login first[/yellow]")
        return

    # 3. Make API call
    status_code, response, error = context.client.make_request(
        "POST",
        "/api/endpoint",
        json_data={"key": args[0]},
    )

    # 4. Handle errors
    if error:
        context.console.print(f"[red]✗ Failed: {error}[/red]")
        context.logger.error(f"Action failed: {error}")
        return

    # 5. Process response
    context.console.print("[green]✓ Success![/green]")
    context.session.some_state = response["data"]
    context.logger.info("Action completed")
```

**Example Actions:**

#### `actions/auth.py` - Authentication Actions

```python
from src.cli.context import CLIContext

def auth_help(context: CLIContext, *args: str) -> None:
    """Show auth commands help."""
    context.console.print("[yellow]Auth Commands:[/yellow]")
    context.console.print("  auth login [username] - Login with username")

def login(context: CLIContext, *args: str) -> None:
    """Handle login."""
    if not args:
        context.console.print("[yellow]Usage: auth login [username][/yellow]")
        return

    username = args[0]
    context.console.print(f"[dim]Logging in as '{username}'...[/dim]")

    status_code, response, error = context.client.make_request(
        "POST",
        "/auth/login",
        json_data={
            "knox_id": username,
            "email": f"{username}@samsung.com",
        },
    )

    if error:
        context.console.print(f"[red]✗ Login failed: {error}[/red]")
        return

    token = response["access_token"]
    context.client.set_token(token)
    context.session.token = token
    context.session.username = username

    context.console.print(f"[green]✓ Logged in as '{username}'[/green]")
```

#### `actions/profile.py` - Profile Actions

```python
from src.cli.context import CLIContext

def profile_help(context: CLIContext, *args: str) -> None:
    """Show profile commands."""
    context.console.print("[yellow]Profile Commands:[/yellow]")
    context.console.print("  profile nickname check [name]    - Check availability")
    context.console.print("  profile nickname register [name] - Register nickname")

def check_nickname_availability(context: CLIContext, *args: str) -> None:
    """Check if nickname is available."""
    if not args:
        context.console.print("[yellow]Usage: profile nickname check [nickname][/yellow]")
        return

    nickname = args[0]

    status_code, response, error = context.client.make_request(
        "POST",
        "/profile/nickname/check",
        json_data={"nickname": nickname},
    )

    if error:
        context.console.print(f"[red]✗ Check failed: {error}[/red]")
        return

    is_available = response.get("available", False)
    if is_available:
        context.console.print(f"[green]✓ '{nickname}' is available[/green]")
    else:
        context.console.print(f"[red]✗ '{nickname}' is taken[/red]")
        suggestions = response.get("suggestions", [])
        if suggestions:
            context.console.print("[dim]Suggestions:[/dim]")
            for s in suggestions:
                context.console.print(f"[dim]  - {s}[/dim]")

def register_nickname(context: CLIContext, *args: str) -> None:
    """Register nickname for authenticated user."""
    if not context.session.token:
        context.console.print("[red]✗ Not authenticated[/red]")
        return

    if not args:
        context.console.print("[yellow]Usage: profile nickname register [nickname][/yellow]")
        return

    nickname = args[0]
    context.client.set_token(context.session.token)

    status_code, response, error = context.client.make_request(
        "POST",
        "/profile/nickname/register",
        json_data={"nickname": nickname},
    )

    if error:
        context.console.print(f"[red]✗ Registration failed: {error}[/red]")
        return

    context.console.print(f"[green]✓ Nickname '{nickname}' registered![/green]")
```

#### `actions/system.py` - System Actions

```python
import os
from collections import defaultdict
from rich.table import Table
from rich.rule import Rule
from src.cli.config.command_layout import COMMAND_LAYOUT

def help(context: CLIContext, *args: str) -> None:
    """Display all available commands."""
    context.console.print("[cyan]Available Commands:[/cyan]")

    # Flatten hierarchical structure
    all_commands = _flatten_commands(COMMAND_LAYOUT)
    all_commands.sort(key=lambda x: x[0])

    # Group by root command
    groups = defaultdict(list)
    for cmd, usage, description in all_commands:
        root = cmd.split()[0]
        groups[root].append((usage, description))

    # Display grouped table
    for group_name in sorted(groups.keys()):
        table = Table(show_header=False, box=None)
        for usage, desc in groups[group_name]:
            table.add_row(usage, f"[dim]{desc}[/dim]")
        context.console.print(table)
        context.console.print(Rule(style="dim"))

def clear(context: CLIContext, *args: str) -> None:
    """Clear terminal screen."""
    os.system("clear" if os.name == "posix" else "cls")
    context.console.print("[green]Welcome back![/green]")

def exit_cli(context: CLIContext, *args: str) -> None:
    """Exit CLI (handled by main loop)."""
    context.console.print("Exiting...")
```

---

## File Structure

```
src/cli/
├── __init__.py
├── main.py                    # CLI class, Dispatcher, main loop
├── context.py                 # CLIContext, SessionState (DI container)
├── client.py                  # APIClient (HTTP wrapper)
├── config/
│   ├── __init__.py
│   ├── command_layout.py      # COMMAND_LAYOUT dictionary
│   ├── models.py              # Pydantic Command/CommandConfig models
│   └── loader.py              # load_config() function
└── actions/
    ├── __init__.py
    ├── auth.py                # Authentication actions
    ├── profile.py             # Profile actions
    ├── questions.py           # Question/test actions
    ├── survey.py              # Survey actions
    ├── agent.py               # Agent actions
    └── system.py              # Help/clear/exit actions
```

---

## How It Works: End-to-End Flow

### User Input: `profile nickname check myname`

```
1. User types: "profile nickname check myname"
   ↓
2. CLI._parse_input(text)
   - Split: ["profile", "nickname", "check", "myname"]
   - Traverse COMMAND_LAYOUT:
     COMMAND_LAYOUT["profile"]["sub_commands"]["nickname"]["sub_commands"]["check"]
   - Result: command_path=["profile","nickname","check"], args=["myname"]
   ↓
3. CLIDispatcher.dispatch(command_path, args)
   - _get_command_target(["profile", "nickname", "check"])
     → "src.cli.actions.profile.check_nickname_availability"
   ↓
4. CLIDispatcher._import_and_get_func(target_path)
   - importlib.import_module("src.cli.actions.profile")
   - getattr(module, "check_nickname_availability")
   - Return: <function check_nickname_availability>
   ↓
5. Execute: func(context, "myname")
   - check_nickname_availability(context, "myname")
   - Makes API call via context.client
   - Displays result via context.console
```

---

## Key Design Patterns

### 1. Config-Driven Design

**Problem:** Hardcoded command routing becomes unmaintainable as CLI grows.

**Solution:** Define all commands in `COMMAND_LAYOUT` dictionary.

**Before (Hardcoded):**
```python
# ❌ Bad: Hardcoded routing
def handle_command(command_parts):
    if command_parts[0] == "profile":
        if command_parts[1] == "nickname":
            if command_parts[2] == "check":
                check_nickname(command_parts[3])
            elif command_parts[2] == "register":
                register_nickname(command_parts[3])
```

**After (Config-Driven):**
```python
# ✅ Good: Config-driven
COMMAND_LAYOUT = {
    "profile": {
        "sub_commands": {
            "nickname": {
                "sub_commands": {
                    "check": {"target": "actions.profile.check_nickname"},
                    "register": {"target": "actions.profile.register_nickname"},
                }
            }
        }
    }
}
```

### 2. Dynamic Dispatcher Pattern

**Problem:** Need to add new commands without modifying dispatcher code.

**Solution:** Use `importlib` to dynamically load handlers at runtime.

```python
def _import_and_get_func(self, target_path: str):
    """
    Dynamic import: "src.cli.actions.profile.check_nickname"
    → Returns actual function object
    """
    module_path, func_name = target_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)
```

**Benefits:**
- Add new command: Just add to `COMMAND_LAYOUT` + create action function
- No dispatcher modification needed
- Easy to test individual actions

### 3. Context-Based Dependency Injection

**Problem:** Actions need access to console, logger, API client, session state.

**Solution:** Pass `CLIContext` to all actions.

```python
@dataclass
class CLIContext:
    console: Console
    logger: Logger
    client: APIClient
    session: SessionState

def my_action(context: CLIContext, *args: str):
    context.console.print("...")  # Access console
    context.logger.info("...")     # Access logger
    context.client.make_request(...)  # Access API client
    context.session.token = "..."     # Access session state
```

**Benefits:**
- No global variables
- Easy to mock in tests
- Clear dependencies

### 4. Hierarchical Command Structure

**Problem:** Flat command space leads to naming collisions and poor UX.

**Solution:** Nested sub-commands with dot notation traversal.

```python
COMMAND_LAYOUT = {
    "profile": {
        "sub_commands": {
            "nickname": {
                "sub_commands": {
                    "check": {...},      # profile nickname check
                    "register": {...},   # profile nickname register
                }
            }
        }
    }
}
```

**Example Commands:**
- `auth login bwyoon`
- `profile nickname check myname`
- `profile nickname register myname`
- `questions session resume`
- `agent tools t1`

---

## Adding New Commands

### Step 1: Define Command in `COMMAND_LAYOUT`

**File:** `src/cli/config/command_layout.py`

```python
COMMAND_LAYOUT = {
    # ... existing commands ...
    "export": {
        "description": "Export test results",
        "usage": "export [subcommand]",
        "target": "src.cli.actions.export.export_help",
        "sub_commands": {
            "csv": {
                "description": "Export to CSV",
                "usage": "export csv [filename]",
                "target": "src.cli.actions.export.export_csv",
            },
            "json": {
                "description": "Export to JSON",
                "usage": "export json [filename]",
                "target": "src.cli.actions.export.export_json",
            }
        }
    }
}
```

### Step 2: Create Action Function

**File:** `src/cli/actions/export.py`

```python
from src.cli.context import CLIContext

def export_help(context: CLIContext, *args: str) -> None:
    """Show export commands."""
    context.console.print("[yellow]Export Commands:[/yellow]")
    context.console.print("  export csv [filename]  - Export to CSV")
    context.console.print("  export json [filename] - Export to JSON")

def export_csv(context: CLIContext, *args: str) -> None:
    """Export results to CSV file."""
    # 1. Validate arguments
    if not args:
        context.console.print("[yellow]Usage: export csv [filename][/yellow]")
        return

    # 2. Check authentication
    if not context.session.token:
        context.console.print("[red]✗ Not authenticated[/red]")
        return

    filename = args[0]

    # 3. Make API call
    context.client.set_token(context.session.token)
    status_code, response, error = context.client.make_request(
        "GET",
        "/export/csv",
        params={"filename": filename},
    )

    # 4. Handle response
    if error:
        context.console.print(f"[red]✗ Export failed: {error}[/red]")
        return

    context.console.print(f"[green]✓ Exported to {filename}[/green]")

def export_json(context: CLIContext, *args: str) -> None:
    """Export results to JSON file."""
    # Similar implementation...
    pass
```

### Step 3: Test

```bash
$ ./tools/dev.sh cli
> export csv results.csv
✓ Exported to results.csv

> export json results.json
✓ Exported to results.json
```

**That's it!** No dispatcher modification needed.

---

## Testing Strategy

### Unit Tests for Actions

```python
# tests/cli/test_export.py
from unittest.mock import MagicMock
from src.cli.actions.export import export_csv
from src.cli.context import CLIContext, SessionState

def test_export_csv_success():
    # Arrange
    console = MagicMock()
    logger = MagicMock()
    client = MagicMock()
    client.make_request.return_value = (200, {"status": "ok"}, None)

    context = CLIContext(
        console=console,
        logger=logger,
        client=client,
        session=SessionState(token="test-token"),
    )

    # Act
    export_csv(context, "test.csv")

    # Assert
    client.make_request.assert_called_once_with(
        "GET",
        "/export/csv",
        params={"filename": "test.csv"},
    )
    console.print.assert_called_with("[green]✓ Exported to test.csv[/green]")

def test_export_csv_not_authenticated():
    context = CLIContext(
        console=MagicMock(),
        logger=MagicMock(),
        session=SessionState(token=None),  # No token
    )

    export_csv(context, "test.csv")

    context.console.print.assert_called_with("[red]✗ Not authenticated[/red]")
```

### Integration Tests

```python
# tests/cli/test_dispatcher.py
from src.cli.main import CLIDispatcher
from src.cli.config.loader import load_config

def test_dispatcher_finds_correct_target():
    config = load_config()
    dispatcher = CLIDispatcher(config, context)

    target = dispatcher._get_command_target(["profile", "nickname", "check"])
    assert target == "src.cli.actions.profile.check_nickname_availability"

def test_dispatcher_imports_function():
    dispatcher = CLIDispatcher(config, context)
    func = dispatcher._import_and_get_func("src.cli.actions.profile.check_nickname_availability")

    assert func is not None
    assert callable(func)
```

---

## Migration Guide: Refactoring Menu-Based CLI to This Architecture

If your existing CLI uses **menu selection** (numbered choices) instead of command-based input, here's how to migrate:

### Before (Menu-Based):

```python
def main_menu():
    print("1. Login")
    print("2. Check Nickname")
    print("3. Register Nickname")
    print("4. Exit")

    choice = input("Select: ")

    if choice == "1":
        username = input("Username: ")
        login(username)
    elif choice == "2":
        nickname = input("Nickname: ")
        check_nickname(nickname)
    elif choice == "3":
        nickname = input("Nickname: ")
        register_nickname(nickname)
    elif choice == "4":
        exit()
```

### After (Command-Based):

#### Step 1: Define Commands

```python
# src/cli/config/command_layout.py
COMMAND_LAYOUT = {
    "auth": {
        "description": "Authentication",
        "sub_commands": {
            "login": {
                "description": "Login",
                "usage": "auth login [username]",
                "target": "src.cli.actions.auth.login",
            }
        }
    },
    "profile": {
        "description": "Profile management",
        "sub_commands": {
            "nickname": {
                "sub_commands": {
                    "check": {
                        "description": "Check nickname availability",
                        "usage": "profile nickname check [name]",
                        "target": "src.cli.actions.profile.check_nickname",
                    },
                    "register": {
                        "description": "Register nickname",
                        "usage": "profile nickname register [name]",
                        "target": "src.cli.actions.profile.register_nickname",
                    }
                }
            }
        }
    }
}
```

#### Step 2: Create Action Functions

```python
# src/cli/actions/auth.py
def login(context: CLIContext, *args: str):
    if not args:
        context.console.print("[yellow]Usage: auth login [username][/yellow]")
        return

    username = args[0]
    # ... implementation ...

# src/cli/actions/profile.py
def check_nickname(context: CLIContext, *args: str):
    if not args:
        context.console.print("[yellow]Usage: profile nickname check [name][/yellow]")
        return

    nickname = args[0]
    # ... implementation ...

def register_nickname(context: CLIContext, *args: str):
    if not args:
        context.console.print("[yellow]Usage: profile nickname register [name][/yellow]")
        return

    nickname = args[0]
    # ... implementation ...
```

#### Step 3: Use CLI Main Loop

Copy `src/cli/main.py`, `src/cli/context.py`, `src/cli/client.py` from this project.

#### Step 4: Run

```bash
$ python -m src.cli.main
> help
Available Commands:
  auth login [username]           - Login
  profile nickname check [name]   - Check nickname availability
  profile nickname register [name] - Register nickname

> auth login bwyoon
✓ Logged in as bwyoon

> profile nickname check myname
✓ 'myname' is available

> profile nickname register myname
✓ Nickname 'myname' registered!
```

---

## Advanced Features

### 1. Auto-Completion

Provided by `prompt_toolkit`:

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

completer = WordCompleter(["auth", "profile", "help", "exit"], ignore_case=True)
session = PromptSession()
text = session.prompt("> ", completer=completer)
```

**User Experience:**
```
> pro<TAB>
> profile <TAB>
> profile nickname <TAB>
> profile nickname check
```

### 2. Command History

```python
from prompt_toolkit.history import InMemoryHistory

session = PromptSession(history=InMemoryHistory())
# User can press ↑/↓ to navigate history
```

### 3. Rich Output Formatting

```python
from rich.console import Console
from rich.table import Table

console = Console()

# Colored output
console.print("[green]✓ Success[/green]")
console.print("[red]✗ Error[/red]")
console.print("[yellow]⚠ Warning[/yellow]")

# Tables
table = Table(title="Results")
table.add_column("ID", style="cyan")
table.add_column("Name", style="magenta")
table.add_row("1", "Alice")
console.print(table)
```

### 4. Session Persistence

```python
# Save session to disk
def save_session(context: CLIContext):
    with open(".session.json", "w") as f:
        json.dump({
            "token": context.session.token,
            "user_id": context.session.user_id,
        }, f)

# Load session on startup
def load_session(context: CLIContext):
    try:
        with open(".session.json", "r") as f:
            data = json.load(f)
            context.session.token = data["token"]
            context.session.user_id = data["user_id"]
    except FileNotFoundError:
        pass
```

### 5. Argument Parsing with Flags

```python
import argparse

def export_csv(context: CLIContext, *args: str):
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--header", action="store_true")

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        context.console.print("[yellow]Usage: export csv [filename] [--delimiter=,] [--header][/yellow]")
        return

    # Use parsed.filename, parsed.delimiter, parsed.header
```

---

## Troubleshooting

### Rich Console Markup Issues

**Problem:** Square brackets in strings are interpreted as markup tags.

```python
# ❌ Wrong: Brackets removed
console.print("Usage: cmd [arg]")  # Output: "Usage: cmd "
```

**Solution:** Use `markup=False` or escape brackets.

```python
# ✅ Correct
console.print("Usage: cmd [arg]", markup=False)

# ✅ Also correct
console.print("Usage: cmd [[arg]]")  # Double brackets
```

### Import Errors

**Problem:** `importlib.import_module` fails silently.

**Solution:** Check target paths in `COMMAND_LAYOUT` match actual module paths.

```python
# COMMAND_LAYOUT
"target": "src.cli.actions.profile.check_nickname_availability"

# File must exist
src/cli/actions/profile.py
  def check_nickname_availability(context, *args): ...
```

### Pydantic Validation Errors

**Problem:** Invalid command structure causes startup crash.

**Solution:** Ensure all commands have required fields:

```python
{
    "description": "...",  # Required
    "target": "module.path.function",  # Required if no sub_commands
    "usage": "...",  # Optional
    "sub_commands": {...}  # Optional
}
```

---

## Benefits of This Architecture

### 1. Maintainability
- **Single source of truth**: All commands in `COMMAND_LAYOUT`
- **No hardcoded routing**: Add commands without touching dispatcher
- **Type safety**: Pydantic validates structure at startup

### 2. Extensibility
- **Easy to add commands**: Just add to config + create action function
- **Hierarchical commands**: Natural grouping (e.g., `profile nickname check`)
- **Dynamic loading**: No recompilation needed

### 3. Testability
- **Pure functions**: Actions are pure functions of `(context, *args)`
- **Easy mocking**: Mock `CLIContext` for unit tests
- **Isolated tests**: Test each action independently

### 4. User Experience
- **Auto-completion**: Tab completion for commands
- **Command history**: Up/down arrow navigation
- **Rich output**: Colors, tables, progress bars
- **Discoverable**: `help` command shows all available commands

### 5. Code Organization
- **Clear separation**: Config / Dispatcher / Actions
- **Consistent patterns**: All actions follow same signature
- **Easy onboarding**: New developers can add commands by following examples

---

## Summary

This CLI architecture provides a **clean, maintainable, and extensible** foundation for building complex command-line interfaces:

**Core Principles:**
1. **Config-Driven**: Define commands in `COMMAND_LAYOUT` dictionary
2. **Dynamic Dispatch**: Load handlers at runtime via `importlib`
3. **Context-Based DI**: Pass `CLIContext` to all actions
4. **Hierarchical Commands**: Support nested sub-commands
5. **Type-Safe**: Pydantic validation for command structure
6. **Consistent Patterns**: All actions use `(context, *args)` signature

**To Apply to Another Project:**
1. Copy core files: `main.py`, `context.py`, `client.py`, `config/`
2. Define your commands in `COMMAND_LAYOUT`
3. Write action functions following `(context, *args)` pattern
4. Run and enjoy!

**Questions to Ask When Reviewing:**
- Are all commands defined in `COMMAND_LAYOUT`?
- Do all action functions follow `(context, *args)` signature?
- Is `CLIContext` used for dependency injection?
- Are target paths correct (`"module.path.function"`)?
- Is Pydantic validation passing at startup?

---

## Example: Complete Minimal CLI

Here's a complete minimal example you can copy and adapt:

```python
# config/command_layout.py
COMMAND_LAYOUT = {
    "greet": {
        "description": "Greet user",
        "usage": "greet [name]",
        "target": "actions.greet.greet_user",
    },
    "help": {
        "description": "Show help",
        "usage": "help",
        "target": "actions.system.help",
    },
}

# actions/greet.py
def greet_user(context, *args):
    if not args:
        context.console.print("[yellow]Usage: greet [name][/yellow]")
        return

    name = args[0]
    context.console.print(f"[green]Hello, {name}![/green]")

# actions/system.py
def help(context, *args):
    context.console.print("[cyan]Commands:[/cyan]")
    context.console.print("  greet [name] - Greet user")
    context.console.print("  help         - Show help")

# main.py
# (Copy from src/cli/main.py)

# Run
$ python main.py
> greet Alice
Hello, Alice!
> help
Commands:
  greet [name] - Greet user
  help         - Show help
```

That's it! You now have a fully functional CLI with config-driven commands, auto-completion, and rich output.
