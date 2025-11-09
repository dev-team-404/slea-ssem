# src/cli/actions/survey.py
from src.cli.context import CLIContext

def get_survey_schema(context: CLIContext, *args):
    """Survey 폼 스키마를 조회합니다."""
    context.console.print(f"[bold green]Executing: get_survey_schema with args: {args}[/bold green]")
    context.logger.info(f"Ran get_survey_schema action with args: {args}.")
    # TODO: 실제 스키마 조회 로직 구현

def submit_survey(context: CLIContext, *args):
    """Survey 데이터를 제출합니다."""
    context.console.print(f"[bold green]Executing: submit_survey with args: {args}[/bold green]")
    context.logger.info(f"Ran submit_survey action with args: {args}.")
    # TODO: 실제 데이터 제출 로직 구현
