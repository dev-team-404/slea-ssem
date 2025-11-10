"""Profile-related CLI actions."""

import re

from src.cli.context import CLIContext


def profile_help(context: CLIContext, *args: str) -> None:
    """Profile 도메인의 사용 가능한 명령어를 보여줍니다."""
    context.console.print("[bold yellow]Profile Commands:[/bold yellow]")
    context.console.print("  profile nickname check        - 닉네임 중복 확인 (인증 불필요)")
    context.console.print("  profile nickname view         - 닉네임 조회 (인증 필요)")
    context.console.print("  profile nickname register     - 닉네임 등록 (인증 필요)")
    context.console.print("  profile nickname edit         - 닉네임 수정 (인증 필요)")
    context.console.print(
        "  profile update_survey         - Survey 업데이트 (인증 필요, 옵션: job_role, duty, interests)"
    )


def check_nickname_availability(context: CLIContext, *args: str) -> None:
    """닉네임 중복 가능 여부를 확인합니다."""
    if not args:
        context.console.print("[bold yellow]Usage:[/bold yellow] profile nickname check [nickname]")
        context.console.print("[bold cyan]Example:[/bold cyan] profile nickname check myname")
        return

    nickname = args[0]
    context.console.print("[dim]Checking nickname availability...[/dim]")

    # API 호출
    status_code, response, error = context.client.make_request(
        "POST",
        "/profile/nickname/check",
        json_data={"nickname": nickname},
    )

    if error:
        context.console.print("[bold red]✗ Check failed[/bold red]")
        context.console.print(f"[red]  Error: {error}[/red]")
        context.logger.error(f"Nickname check failed: {error}")
        return

    if status_code not in (200, 201):
        context.console.print(f"[bold red]✗ Check failed (HTTP {status_code})[/bold red]")
        return

    is_available = response.get("available", False)
    if is_available:
        context.console.print(f"[bold green]✓ Nickname '{nickname}' is available[/bold green]")
    else:
        suggestions = response.get("suggestions", [])
        context.console.print(f"[bold red]✗ Nickname '{nickname}' is not available[/bold red]")
        if suggestions:
            context.console.print("[dim]  Suggestions:[/dim]")
            for suggestion in suggestions:
                context.console.print(f"[dim]    - {suggestion}[/dim]")
    context.logger.info(f"Checked nickname availability for: {nickname}.")


def view_nickname(context: CLIContext, *args: str) -> None:
    """현재 사용자의 닉네임 정보를 조회합니다."""
    if not context.session.token:
        context.console.print("[bold red]✗ Not authenticated[/bold red]")
        context.console.print("[yellow]Please login first: auth login [username][/yellow]")
        return

    context.console.print("[dim]Fetching nickname information...[/dim]")

    # JWT 토큰을 client에 설정
    context.client.set_token(context.session.token)

    # API 호출
    status_code, response, error = context.client.make_request(
        "GET",
        "/profile/nickname",
    )

    if error:
        context.console.print("[bold red]✗ Failed to fetch nickname[/bold red]")
        context.console.print(f"[red]  Error: {error}[/red]")
        context.logger.error(f"Nickname fetch failed: {error}")
        return

    if status_code != 200:
        context.console.print(f"[bold red]✗ Failed (HTTP {status_code})[/bold red]")
        return

    nickname = response.get("nickname")
    registered_at = response.get("registered_at")
    updated_at = response.get("updated_at")

    if nickname:
        context.console.print(f"[bold green]✓ Nickname:[/bold green] {nickname}")
        if registered_at:
            context.console.print(f"[dim]  Registered: {registered_at}[/dim]")
        if updated_at:
            context.console.print(f"[dim]  Updated: {updated_at}[/dim]")
    else:
        context.console.print("[bold yellow]✓ No nickname set yet[/bold yellow]")
    context.logger.info("Fetched nickname information.")


def register_nickname(context: CLIContext, *args: str) -> None:
    """닉네임을 등록합니다."""
    if not context.session.token:
        context.console.print("[bold red]✗ Not authenticated[/bold red]")
        context.console.print("[yellow]Please login first: auth login [username][/yellow]")
        return

    if not args:
        context.console.print("[bold yellow]Usage:[/bold yellow] profile nickname register [nickname]")
        context.console.print("[bold cyan]Example:[/bold cyan] profile nickname register myname")
        return

    nickname = args[0]
    context.console.print(f"[dim]Registering nickname '{nickname}'...[/dim]")

    # JWT 토큰을 client에 설정
    context.client.set_token(context.session.token)

    # API 호출
    status_code, response, error = context.client.make_request(
        "POST",
        "/profile/register",
        json_data={"nickname": nickname},
    )

    if error:
        context.console.print("[bold red]✗ Registration failed[/bold red]")
        context.console.print(f"[red]  Error: {error}[/red]")
        context.logger.error(f"Nickname registration failed: {error}")
        return

    if status_code not in (200, 201):
        context.console.print(f"[bold red]✗ Registration failed (HTTP {status_code})[/bold red]")
        return

    context.console.print(f"[bold green]✓ Nickname '{nickname}' registered[/bold green]")
    context.logger.info(f"Registered nickname: {nickname}.")


def edit_nickname(context: CLIContext, *args: str) -> None:
    """닉네임을 수정합니다."""
    if not context.session.token:
        context.console.print("[bold red]✗ Not authenticated[/bold red]")
        context.console.print("[yellow]Please login first: auth login [username][/yellow]")
        return

    if len(args) < 1:
        context.console.print("[bold yellow]Usage:[/bold yellow] profile nickname edit [new_nickname]")
        context.console.print("[bold cyan]Example:[/bold cyan] profile nickname edit newname")
        return

    new_nickname = args[0]
    context.console.print(f"[dim]Updating nickname to '{new_nickname}'...[/dim]")

    # JWT 토큰을 client에 설정
    context.client.set_token(context.session.token)

    # API 호출
    status_code, response, error = context.client.make_request(
        "PUT",
        "/profile/nickname",
        json_data={"nickname": new_nickname},
    )

    if error:
        context.console.print("[bold red]✗ Update failed[/bold red]")
        context.console.print(f"[red]  Error: {error}[/red]")
        context.logger.error(f"Nickname update failed: {error}")
        return

    if status_code not in (200, 201):
        context.console.print(f"[bold red]✗ Update failed (HTTP {status_code})[/bold red]")
        return

    context.console.print(f"[bold green]✓ Nickname updated to '{new_nickname}'[/bold green]")
    context.logger.info(f"Nickname changed to {new_nickname}.")


def update_survey(context: CLIContext, *args: str) -> None:
    """Survey를 업데이트하여 새 프로필 레코드를 생성합니다."""
    if not context.session.token:
        context.console.print("[bold red]✗ Not authenticated[/bold red]")
        context.console.print("[yellow]Please login first: auth login [username][/yellow]")
        return

    if len(args) < 2:
        context.console.print("[bold yellow]Usage:[/bold yellow]")
        context.console.print(
            "  profile update_survey [level] [years] [--job_role ROLE] [--duty DUTY] [--interests ITEM1,ITEM2,...]",
            markup=False,
        )
        context.console.print("[bold dim]level:[/bold dim] beginner | intermediate | advanced")
        context.console.print("[bold dim]years:[/bold dim] 0-60 (years of experience)")
        context.console.print("[bold cyan]Examples:[/bold cyan]")
        context.console.print("  profile update_survey beginner 0")
        context.console.print("  profile update_survey intermediate 5 --interests 'AI,ML,NLP'")
        context.console.print(
            "  profile update_survey advanced 10 --job_role 'Senior Dev' --duty 'Architecture' --interests 'AI,ML'"
        )
        return

    level = args[0]
    career_input = args[1]

    # Parse career (years_experience) - extract integer from input
    try:
        # Try to parse as integer directly first
        years_experience = int(career_input)
    except ValueError:
        # If that fails, try to extract number from string like "5years"
        match = re.search(r"\d+", career_input)
        if match:
            years_experience = int(match.group())
        else:
            context.console.print("[bold red]✗ Invalid career value[/bold red]")
            context.console.print("[yellow]Career must be a number (0-60) or string like '5years'[/yellow]")
            return

    # Validate range
    if not (0 <= years_experience <= 60):
        context.console.print("[bold red]✗ Invalid career value[/bold red]")
        context.console.print("[yellow]Years of experience must be between 0 and 60[/yellow]")
        return

    career = years_experience
    job_role = None
    duty = None
    interests_str = None

    # Parse optional flags
    i = 2
    while i < len(args):
        if args[i] == "--job_role" and i + 1 < len(args):
            job_role = args[i + 1]
            i += 2
        elif args[i] == "--duty" and i + 1 < len(args):
            duty = args[i + 1]
            i += 2
        elif args[i] == "--interests" and i + 1 < len(args):
            interests_str = args[i + 1]
            i += 2
        else:
            context.console.print(f"[yellow]Unknown option: {args[i]}[/yellow]")
            i += 1

    context.console.print("[dim]Updating survey...[/dim]")

    # JWT 토큰을 client에 설정
    context.client.set_token(context.session.token)

    # Prepare JSON data
    json_data = {
        "level": level,
        "career": career,
    }

    # Add optional fields if provided
    if job_role:
        json_data["job_role"] = job_role
    if duty:
        json_data["duty"] = duty
    if interests_str:
        # Convert comma-separated string to list
        interests = [item.strip() for item in interests_str.split(",")]
        json_data["interests"] = interests

    # API 호출
    status_code, response, error = context.client.make_request(
        "PUT",
        "/profile/survey",
        json_data=json_data,
    )

    if error:
        context.console.print("[bold red]✗ Update failed[/bold red]")
        context.console.print(f"[red]  Error: {error}[/red]")
        context.logger.error(f"Survey update failed: {error}")
        return

    if status_code not in (200, 201):
        context.console.print(f"[bold red]✗ Update failed (HTTP {status_code})[/bold red]")
        return

    context.console.print("[bold green]✓ Profile survey updated[/bold green]")
    context.console.print("[dim]  New profile record created[/dim]")
    context.logger.info(
        f"Survey updated: level={level}, career={career}, job_role={job_role}, duty={duty}, interests={interests_str}."
    )
