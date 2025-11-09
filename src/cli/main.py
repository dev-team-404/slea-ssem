import importlib
import logging
import sys
import atexit
from typing import Dict, List, Optional, Tuple

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from src.cli.config.loader import load_config
from src.cli.config.models import Command, CommandConfig
from src.cli.context import CLIContext

# Configure logging
logging.basicConfig(level=logging.DEBUG, stream=sys.stderr,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CLIDispatcher:
    def __init__(self, command_config: CommandConfig, context: CLIContext):
        self.command_config = command_config
        self.context = context
        self.console = context.console
        self.logger = context.logger

    def _get_command_target(self, command_path: List[str]) -> Optional[str]:
        """주어진 명령어 경로에 해당하는 실행 함수 경로를 찾습니다."""
        self.logger.debug(f"Attempting to get command target for: {command_path}")
        current_level = self.command_config.commands
        target = None
        for i, cmd_name in enumerate(command_path):
            if cmd_name in current_level:
                cmd_obj = current_level[cmd_name]
                if i == len(command_path) - 1:  # 마지막 명령어
                    target = cmd_obj.target
                if cmd_obj.sub_commands:
                    current_level = cmd_obj.sub_commands
                else: # 하위 명령어가 없는데 경로가 더 있으면 잘못된 경로
                    self.logger.debug(f"No sub-commands for {cmd_name}, breaking path search.")
                    break
            else:
                self.logger.debug(f"Command '{cmd_name}' not found at current level.")
                return None # 명령어를 찾을 수 없음
        self.logger.debug(f"Found target: {target} for command path: {command_path}")
        return target

    def _import_and_get_func(self, target_path: str):
        """'module.function' 문자열로부터 함수 객체를 임포트하고 반환합니다."""
        self.logger.debug(f"Attempting to import function from target path: {target_path}")
        try:
            module_path, func_name = target_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            self.logger.debug(f"Successfully imported function: {func_name} from {module_path}")
            return func
        except (ImportError, AttributeError) as e:
            self.logger.error(f"Error loading command: {target_path} - {e}")
            self.console.print(f"[bold red]Error loading command: {target_path} - {e}[/bold red]")
            return None

    def dispatch(self, command_path: List[str], args: List[str]):
        """
        명령어 경로와 인자를 기반으로 해당 함수를 찾아 실행합니다.
        """
        self.logger.info(f"Dispatching command: {command_path} with args: {args}")
        if not command_path:
            self.console.print("[bold red]No command entered.[/bold red]")
            self.logger.warning("Dispatch called with empty command_path.")
            return

        # 'help'와 'exit'는 특별 처리
        if command_path[0] == "help":
            self.logger.debug("Handling 'help' command.")
            target_path = self._get_command_target(["help"])
            if target_path:
                func = self._import_and_get_func(target_path)
                if func:
                    func(self.context, *args) # help 함수는 context와 args를 받음
            return
        elif command_path[0] == "exit":
            self.logger.debug("Handling 'exit' command.")
            self.context.console.print("Exiting CLI...")
            return

        target_path = self._get_command_target(command_path)

        if target_path:
            func = self._import_and_get_func(target_path)
            if func:
                self.logger.debug(f"Executing function for target: {target_path}")
                try:
                    # 모든 액션 함수는 CLIContext를 첫 번째 인자로 받도록 가정
                    func(self.context, *args)
                    self.logger.debug(f"Command '{' '.join(command_path)}' executed successfully.")
                except Exception as e:
                    self.logger.error(f"Error executing command '{' '.join(command_path)}': {e}", exc_info=True)
                    self.console.print(f"[bold red]Error executing command '{' '.join(command_path)}': {e}[/bold red]")
            else:
                self.logger.warning(f"Could not find executable for command: {' '.join(command_path)}")
                self.console.print(f"[bold red]Could not find executable for command: {' '.join(command_path)}[/bold red]")
        else:
            self.logger.warning(f"Unknown command: {' '.join(command_path)}")
            self.console.print(f"[bold red]Unknown command: {' '.join(command_path)}[/bold red]")
            self.console.print("[bold yellow]Type 'help' to see available commands.[/bold yellow]")


class CLI:
    def __init__(self):
        self.console = Console()
        self.logger = logger # Use the module-level logger
        self.context = CLIContext(console=self.console, logger=self.logger)
        self.command_config = load_config()
        self.dispatcher = CLIDispatcher(self.command_config, self.context)
        self.session = PromptSession(history=InMemoryHistory())
        self.should_exit = False  # Flag to signal exit
        self.logger.info("CLI initialized.")

        # Register cleanup handler for graceful shutdown
        atexit.register(self._cleanup)

    def _get_completer(self, current_commands: Dict[str, Command]) -> WordCompleter:
        """현재 레벨의 명령어들을 위한 자동 완성 기능을 생성합니다."""
        words = list(current_commands.keys())
        self.logger.debug(f"Completer words: {words}")
        return WordCompleter(words, ignore_case=True)

    def _parse_input(self, text: str) -> Tuple[List[str], List[str]]:
        """입력 문자열을 명령어 경로와 인자로 분리합니다."""
        self.logger.debug(f"Parsing input: '{text}'")
        parts = text.strip().split()
        if not parts:
            self.logger.debug("Input is empty.")
            return [], []

        command_path = []
        args = []
        current_level = self.command_config.commands

        for i, part in enumerate(parts):
            if part in current_level:
                command_path.append(part)
                if current_level[part].sub_commands:
                    current_level = current_level[part].sub_commands
                else: # 더 이상 하위 명령어가 없으면 나머지는 모두 인자
                    args = parts[i+1:]
                    self.logger.debug(f"No more sub-commands, remaining parts are args: {args}")
                    break
            else: # 현재 레벨에서 명령어를 찾을 수 없으면 나머지는 모두 인자
                args = parts[i:]
                self.logger.debug(f"Command part '{part}' not found, remaining parts are args: {args}")
                break
        self.logger.debug(f"Parsed command_path: {command_path}, args: {args}")
        return command_path, args

    def _cleanup(self):
        """CLI 종료 시 정리 작업을 수행합니다."""
        self.logger.info("Cleaning up CLI resources...")
        # prompt_toolkit 리소스 정리
        try:
            # PromptSession 종료 (있다면)
            if hasattr(self.session, 'app') and self.session.app:
                self.session.app.exit()
        except Exception as e:
            self.logger.debug(f"Error during prompt_toolkit cleanup: {e}")

        self.logger.info("CLI cleanup completed.")

    def run(self):
        self.console.print("[bold green]Welcome to the SLEA-SSEM CLI![/bold green]")
        self.console.print("[bold yellow]Type 'help' for a list of commands, or 'exit' to quit.[/bold yellow]")
        self.logger.info("CLI started. Entering main loop.")

        exit_count = 0  # Track consecutive Ctrl+C presses

        while True:
            try:
                # Check if exit flag was set
                if self.should_exit:
                    self.logger.info("Exit flag set, breaking loop.")
                    break

                self.logger.debug("Before session.prompt()")
                completer = self._get_completer(self.command_config.commands)

                text = self.session.prompt("> ", completer=completer)
                self.logger.debug(f"After session.prompt(), received text: '{text}'")

                # Reset exit counter on successful input
                exit_count = 0

                command_path, args = self._parse_input(text)

                if not command_path:
                    self.logger.debug("Empty command path, continuing loop.")
                    continue

                if command_path[0] == "exit":
                    self.logger.info("Exit command received. Dispatching and breaking loop.")
                    self.dispatcher.dispatch(command_path, args) # 메시지 출력용
                    self.should_exit = True
                    break # 루프 종료

                self.dispatcher.dispatch(command_path, args)

            except KeyboardInterrupt:
                exit_count += 1
                self.logger.info(f"KeyboardInterrupt received (count: {exit_count}).")
                if exit_count >= 2:
                    self.console.print("\n[bold red]Force exiting...[/bold red]")
                    self.logger.warning("Multiple Ctrl-C detected. Force exiting.")
                    self.should_exit = True
                    break
                self.console.print("\n[bold yellow]Ctrl-C pressed. Press Ctrl-C again to force exit, or type 'exit'.[/bold yellow]")
            except EOFError:
                self.logger.info("EOFError received. Breaking loop.")
                self.console.print("\n[bold yellow]EOF received. Exiting...[/bold yellow]")
                self.should_exit = True
                break
            except Exception as e:
                self.logger.critical(f"An unexpected error occurred: {e}", exc_info=True)
                self.console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")

def main():
    """Main entry point for the CLI."""
    try:
        cli = CLI()
        cli.run()
        logger.info("CLI run() completed successfully.")
    except KeyboardInterrupt:
        logger.info("CLI interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in CLI: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("CLI shutdown initiated.")
        # Ensure clean exit
        sys.exit(0)

if __name__ == "__main__":
    main()
