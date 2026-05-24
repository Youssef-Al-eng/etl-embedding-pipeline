"""
PipelineReporter — Beautiful terminal output using rich (falls back to plain text).
"""

import sys
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    from rich.rule import Rule
    from rich.columns import Columns
    from rich.progress import Progress
    RICH = True
except ImportError:
    RICH = False

console = Console() if RICH else None


def _plain(*args):
    print(*args)


class PipelineReporter:
    def pipeline_start(self, config):
        if RICH:
            console.print()
            console.print(Panel.fit(
                Text("⚡ EMBEDDING PIPELINE", style="bold white", justify="center"),
                subtitle=f"[dim]model: {config.embedding_model}  •  batch: {config.batch_size}  •  concurrency: {config.max_concurrent}[/dim]",
                border_style="bright_cyan",
                padding=(0, 4),
            ))
            console.print(f"  [dim]Data dir:[/dim]  [cyan]{config.data_dir}[/cyan]")
            console.print(f"  [dim]Output  :[/dim]  [cyan]{config.output_dir}[/cyan]")
            mode = "[yellow]DEMO MODE — random embeddings (set OPENAI_API_KEY for real)[/yellow]" if not config.openai_api_key else "[green]Live OpenAI API[/green]"
            console.print(f"  [dim]Mode    :[/dim]  {mode}")
            console.print()
        else:
            _plain("=" * 60)
            _plain("  EMBEDDING PIPELINE STARTED")
            _plain(f"  Model: {config.embedding_model} | Batch: {config.batch_size}")
            _plain("=" * 60)

    def file_start(self, name: str):
        if RICH:
            console.print(f"\n[bold cyan]▶[/bold cyan] [bold]{name}[/bold]")
        else:
            _plain(f"\n>> Processing: {name}")

    def cleaning_report(self, name: str, report: dict):
        dropped = report["original_rows"] - report["final_rows"]
        pct = (dropped / report["original_rows"] * 100) if report["original_rows"] else 0
        if RICH:
            console.print(
                f"  [dim]Cleaning:[/dim] "
                f"[white]{report['original_rows']:,}[/white] rows → "
                f"[green]{report['final_rows']:,}[/green] clean "
                f"[dim](dropped {dropped:,} = {pct:.1f}%)[/dim]"
            )
        else:
            _plain(f"  Cleaning: {report['original_rows']} → {report['final_rows']} rows")

    def resume_notice(self, name: str, done: int, total: int):
        if RICH:
            console.print(
                f"  [yellow]⚡ Resuming:[/yellow] {done}/{total} batches already completed"
            )
        else:
            _plain(f"  Resuming: {done}/{total} batches done")

    def file_done(self, stats: dict):
        if RICH:
            status = "[green]✓ Done[/green]"
            if stats.get("skipped"):
                status = "[yellow]⚠ Skipped (no clean data)[/yellow]"
            elif stats.get("errors", 0) > 0:
                status = f"[yellow]✓ Done ({stats['errors']} retried)[/yellow]"
            console.print(
                f"  [dim]Result:[/dim] {status}  "
                f"[dim]embeddings:[/dim] [bold green]{stats.get('embeddings_saved', 0):,}[/bold green]"
            )
        else:
            _plain(f"  Done: {stats.get('embeddings_saved', 0)} embeddings saved")

    def no_files_found(self, data_dir: str):
        if RICH:
            console.print(Panel(
                f"[yellow]No CSV files found in '[bold]{data_dir}[/bold]'.\n\n"
                "Place your .csv files there and re-run the pipeline.[/yellow]",
                title="[bold yellow]⚠ Nothing to process[/bold yellow]",
                border_style="yellow",
            ))
        else:
            _plain(f"No CSV files found in '{data_dir}'")

    def pipeline_summary(self, all_stats: list, elapsed: float, log_file: str):
        total_rows = sum(s.get("rows_clean", 0) for s in all_stats)
        total_embeddings = sum(s.get("embeddings_saved", 0) for s in all_stats)
        total_errors = sum(s.get("errors", 0) for s in all_stats)
        files_ok = sum(1 for s in all_stats if not s.get("fatal_error") and not s.get("skipped"))

        if RICH:
            console.print()
            console.rule("[bold cyan]Pipeline Complete[/bold cyan]")
            console.print()

            table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan")
            table.add_column("File", style="white")
            table.add_column("Rows (clean)", justify="right", style="green")
            table.add_column("Embeddings", justify="right", style="bold green")
            table.add_column("Errors", justify="right", style="yellow")
            table.add_column("Status")

            for s in all_stats:
                if s.get("fatal_error"):
                    table.add_row(s["file"], "—", "—", "—", f"[red]✗ Fatal: {s['fatal_error'][:40]}[/red]")
                elif s.get("skipped"):
                    table.add_row(s["file"], "0", "0", "0", "[yellow]⚠ Skipped[/yellow]")
                else:
                    table.add_row(
                        s["file"],
                        f"{s.get('rows_clean', 0):,}",
                        f"{s.get('embeddings_saved', 0):,}",
                        str(s.get("errors", 0)) if s.get("errors", 0) else "[dim]0[/dim]",
                        "[green]✓[/green]",
                    )

            console.print(table)

            mins, secs = divmod(int(elapsed), 60)
            speed = total_embeddings / elapsed if elapsed else 0
            console.print(
                f"  [bold]Files:[/bold] {files_ok}/{len(all_stats)}  "
                f"[bold]Rows:[/bold] {total_rows:,}  "
                f"[bold]Embeddings:[/bold] {total_embeddings:,}  "
                f"[bold]Time:[/bold] {mins}m {secs}s  "
                f"[bold]Speed:[/bold] {speed:.0f} emb/s"
            )
            console.print(f"  [dim]Logs saved to: {log_file}[/dim]")
            console.print()
        else:
            _plain("\n" + "=" * 60)
            _plain("  PIPELINE SUMMARY")
            _plain(f"  Files: {files_ok}/{len(all_stats)}")
            _plain(f"  Total embeddings: {total_embeddings:,}")
            _plain(f"  Time: {elapsed:.1f}s")
            _plain("=" * 60)
