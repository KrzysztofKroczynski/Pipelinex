import sys
from pathlib import Path

import click

# Force UTF-8 stdout/stderr on Windows (avoids charmap errors with model output)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .loader import load_pipeline, validate_pipeline
from .runner import PipelineRunner
from .scaffold import scaffold_pipeline, scaffold_step, scaffold_tool
from .tools.builtin import BUILTIN_SCHEMAS
from .tools.resolver import GLOBAL_TOOLS_PATH, install_tool_deps, resolve_tools


@click.group()
def main():
    """pipelinex — folder-based agentic AI pipeline framework"""


@main.command()
@click.argument("pipeline_path", type=click.Path(exists=True))
@click.option("--input", "input_data", default=None, help="Input text or path to input file")
@click.option("--from", "from_step", default=None, metavar="STEP_ID", help="Resume from this step")
@click.option("--dry-run", is_flag=True, help="Validate config and env, don't execute")
@click.option("--watch", is_flag=True, help="Show live step/tool progress")
@click.option("--model", "model_override", default=None, metavar="PROVIDER/NAME", help="Override model")
def run(pipeline_path, input_data, from_step, dry_run, watch, model_override):
    """Run a pipeline."""
    path = Path(pipeline_path)

    try:
        config = load_pipeline(path)
    except (FileNotFoundError, SystemExit) as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)

    errors = validate_pipeline(config)
    if errors:
        click.echo("Validation errors:", err=True)
        for e in errors:
            click.echo(f"  - {e}", err=True)
        sys.exit(1)

    if dry_run:
        click.echo("Pipeline config valid.")
        click.echo(f"  Name:    {config.get('name')}")
        click.echo(f"  Version: {config.get('version')}")
        click.echo(f"  Model:   {config['model']['provider']}/{config['model']['name']}")
        click.echo(f"  Steps:   {[s['id'] for s in config.get('steps', [])]}")
        return

    if input_data:
        p = Path(input_data)
        if p.exists():
            input_data = p.read_text(encoding="utf-8")

    runner = PipelineRunner(
        pipeline_path=path,
        watch=watch,
        from_step=from_step,
        model_override=model_override,
        input_data=input_data,
    )

    try:
        runner.run()
    except SystemExit as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\nInterrupted.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("args", nargs=-1)
@click.option("--in", "in_dir", default=None, help="Target directory")
def new(args, in_dir):
    """Scaffold a pipeline, step, or tool.

    \b
    pipelinex new my-pipeline
    pipelinex new step step-05-review --in ./my-pipeline
    pipelinex new tool send_email --in ./my-pipeline/tools
    """
    if not args:
        click.echo("Usage:")
        click.echo("  pipelinex new <pipeline-name>")
        click.echo("  pipelinex new step <step-id> --in <pipeline-dir>")
        click.echo("  pipelinex new tool <tool-name> --in <tools-dir>")
        return

    if args[0] == "step":
        if len(args) < 2:
            click.echo("ERROR: step name required. Usage: pipelinex new step <step-id> --in <pipeline-dir>", err=True)
            sys.exit(1)
        scaffold_step(args[1], Path(in_dir or "."))

    elif args[0] == "tool":
        if len(args) < 2:
            click.echo("ERROR: tool name required. Usage: pipelinex new tool <name> --in <tools-dir>", err=True)
            sys.exit(1)
        scaffold_tool(args[1], Path(in_dir or "tools"))

    else:
        scaffold_pipeline(args[0], Path(in_dir or "."))


@main.command()
@click.argument("pipeline_path", type=click.Path(exists=True))
def validate(pipeline_path):
    """Validate pipeline config without running."""
    path = Path(pipeline_path)
    try:
        config = load_pipeline(path)
    except (FileNotFoundError, SystemExit) as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)

    errors = validate_pipeline(config)
    if errors:
        click.echo("Validation failed:")
        for e in errors:
            click.echo(f"  x {e}")
        sys.exit(1)

    click.echo("OK Pipeline is valid")
    click.echo(f"  Steps: {[s['id'] for s in config.get('steps', [])]}")
    click.echo(f"  Model: {config['model']['provider']}/{config['model']['name']}")


@main.group()
def tools():
    """Manage tools."""


@tools.command("list")
@click.option("--pipeline", "pipeline_path", default=None, help="Include pipeline-level tools")
def tools_list(pipeline_path):
    """List available tools."""
    click.echo("Built-in tools:")
    for t in BUILTIN_SCHEMAS:
        click.echo(f"  {t['name']:<20} {t['description'][:60]}")

    if pipeline_path:
        path = Path(pipeline_path)
        custom = [t for t in resolve_tools(path) if t["name"] not in {s["name"] for s in BUILTIN_SCHEMAS}]
        if custom:
            click.echo(f"\nPipeline tools ({path.name}):")
            for t in custom:
                click.echo(f"  {t['name']}")

    if GLOBAL_TOOLS_PATH.exists():
        global_tools = list(GLOBAL_TOOLS_PATH.iterdir())
        if global_tools:
            click.echo(f"\nGlobal tools (~/.pipelinex/tools/):")
            for d in global_tools:
                if d.is_dir():
                    click.echo(f"  {d.name}")


@tools.command("install")
@click.argument("pipeline_path", type=click.Path(exists=True))
def tools_install(pipeline_path):
    """Install tool deps for a pipeline without running."""
    path = Path(pipeline_path)
    cache = Path.home() / ".pipelinex"
    count = 0

    for tools_dir in _all_tool_dirs(path):
        if not tools_dir.exists():
            continue
        for tool_dir in tools_dir.iterdir():
            if tool_dir.is_dir() and (tool_dir / "tool.json").exists():
                try:
                    install_tool_deps(tool_dir, cache)
                    count += 1
                except Exception as e:
                    click.echo(f"  Failed {tool_dir.name}: {e}", err=True)

    click.echo(f"Installed deps for {count} tool(s).")


def _all_tool_dirs(pipeline_path: Path):
    yield pipeline_path / "tools"
    try:
        config = load_pipeline(pipeline_path)
        for step in config.get("steps", []):
            yield pipeline_path / step["id"] / "tools"
    except Exception:
        pass


@main.command()
@click.argument("pipeline_path", type=click.Path(exists=True))
@click.option("--errors", is_flag=True, help="Show error report from last failed run")
def log(pipeline_path, errors):
    """Show run log or error report."""
    path = Path(pipeline_path)

    if errors:
        report = path / "output" / "errors" / "report.md"
        if report.exists():
            click.echo(report.read_text(encoding="utf-8"))
        else:
            click.echo("No error report found.")
    else:
        log_file = path / "output" / "run.log"
        if log_file.exists():
            click.echo(log_file.read_text(encoding="utf-8"))
        else:
            click.echo("No run log found.")
