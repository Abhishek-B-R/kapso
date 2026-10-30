"""`kapso report`: a campaign as a shareable Markdown summary.

A pure reader over what the campaign already wrote: the run checkpoint,
the status file, the launch record, the inbox and the experiment
branches. It never writes into the campaign and makes no model calls.
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from kapso.execution.cost_estimator import campaign_cost_used, effective_cost
from kapso.execution.fidelity import full_eval_score
from kapso.execution.inbox import (
    Request,
    idea_line,
    inbox_path,
    load_requests,
    read_launch_record,
)
from kapso.execution.observability import OperationStatusView, platform_cost_summary
from kapso.execution.run_checkpoint import RunCheckpoint, RunCheckpointStore
from kapso.execution.search_strategies.base import SearchNode
from kapso.execution.search_strategies.generic.strategy import (
    rank_candidates,
    select_deliverable,
)


def render_campaign_report(campaign: str | Path, *, top: int) -> str:
    """The report for the campaign at `campaign`, with `top` leaderboard
    rows. A directory without a checkpoint or a status file raises, and
    so does any corrupt state file."""
    if isinstance(top, bool) or not isinstance(top, int) or top < 1:
        raise ValueError(f"top must be a positive integer, got {top!r}")
    campaign = Path(campaign).expanduser()
    checkpoint = RunCheckpointStore(str(campaign)).load()
    status = OperationStatusView(campaign)
    history = checkpoint.strategy_state.get("node_history")
    if not isinstance(history, list):
        raise ValueError(f"{campaign} checkpoint has no node history")
    nodes = [SearchNode.from_dict(node) for node in history]
    selection_config = {
        "cost": checkpoint.cost_config,
        "maximize_scoring": checkpoint.maximize_scoring,
    }
    ranked = rank_candidates(nodes, selection_config)
    evaluator_id = checkpoint.strategy_state.get("scores_evaluator_id", "")
    deliverable = select_deliverable(
        nodes, evaluator_id=evaluator_id, selection_config=selection_config
    )
    leaders = ranked[:top]
    sections = [
        _summary(campaign, checkpoint, status, nodes),
        _deliverable(deliverable, evaluator_id),
        _leaderboard(leaders, len(ranked), checkpoint.cost_config),
        _lineage(status),
        _changes(campaign, leaders),
        _human_input(load_requests(inbox_path(campaign))),
        _outcomes(nodes, len(ranked)),
    ]
    return "\n\n".join(sections) + "\n"


def _summary(
    campaign: Path,
    checkpoint: RunCheckpoint,
    status: OperationStatusView,
    nodes: Sequence[SearchNode],
) -> str:
    launch = read_launch_record(campaign) or {}
    state = status.state
    if status.dead:
        state += " (its process is gone)"
    elif status.stalled:
        state += " (stalled)"
    reason = status.data.get("stopped_reason")
    detail = status.data.get("stop_detail")
    if reason:
        state += f", stopped: {reason}" + (
            f" ({detail})" if detail and detail != reason else ""
        )
    if status.data.get("error"):
        state += f", error: {status.data['error']}"
    lines = ["# Campaign report", ""]
    lines.extend(f"> {line}".rstrip() for line in checkpoint.goal.strip().splitlines())
    lines.extend([
        "",
        f"- **State:** {state}",
        f"- **As of:** {status.data['heartbeat_at']}",
        "- **Iterations:** "
        + _against(str(checkpoint.completed_iterations), launch.get("experiments")),
        "- **Elapsed:** "
        + _against(
            f"{checkpoint.elapsed_seconds / 60:.1f}",
            launch.get("minutes"),
        )
        + " min",
        "- **Model spend:** "
        + _against(
            f"${checkpoint.cumulative_cost:.2f}",
            None if launch.get("usd") is None
            else f"${float(launch['usd']):.2f}",
        ),
    ])
    cost_config = checkpoint.cost_config
    if cost_config["enabled"]:
        platform = platform_cost_summary({
            "used": campaign_cost_used(nodes, cost_config),
            "budget": cost_config["campaign_budget"],
            "unit": cost_config["unit"],
            "refused": sum(1 for node in nodes if node.cost_refusal),
        })
        lines.append(f"- **Platform cost:** {platform}")
    return "\n".join(lines)


def _against(value: str, budget: Any) -> str:
    return value if budget is None else f"{value} of {budget}"


def _deliverable(node: Optional[SearchNode], evaluator_id: str) -> str:
    if node is None:
        return "## Deliverable\n\nNo scored candidate yet."
    full_score = full_eval_score(node, evaluator_id) if evaluator_id else None
    lines = [
        "## Deliverable",
        "",
        f"- **Node:** {node.node_id}",
        f"- **Branch:** `{node.branch_name}`",
        f"- **Score:** {_score(node.score if full_score is None else full_score)}",
    ]
    idea = idea_line(node.solution)
    if idea:
        lines.append(f"- **Idea:** {idea}")
    if node.metrics:
        metrics = ", ".join(
            f"{name} {value:.6g}" + (" (primary)" if name == node.primary_metric else "")
            for name, value in node.metrics.items()
        )
        lines.append(f"- **External metrics:** {metrics}")
    return "\n".join(lines)


def _leaderboard(
    leaders: Sequence[SearchNode], scored: int, cost_config: Dict[str, Any]
) -> str:
    if not leaders:
        return "## Leaderboard\n\nNo scored candidate yet."
    with_cost = cost_config["enabled"]
    header = ["Rank", "Node", "Score"]
    if with_cost:
        header.append(f"Cost ({cost_config['unit']})")
    header.extend(["Parent", "Branch", "Idea"])
    rows = []
    for rank, node in enumerate(leaders, start=1):
        row = [str(rank), str(node.node_id), _score(node.score)]
        if with_cost:
            row.append(f"{effective_cost(node, cost_config):g}")
        row.extend([
            "main" if node.parent_node_id is None else str(node.parent_node_id),
            f"`{node.branch_name}`",
            idea_line(node.solution),
        ])
        rows.append(row)
    return "\n".join([
        "## Leaderboard",
        "",
        f"Top {len(leaders)} of {scored} scored candidates, in the campaign's own ranking.",
        "",
        _table(header, rows),
    ])


def _lineage(status: OperationStatusView) -> str:
    # The same rows the status view draws, without the screen's blank line
    # and "campaign tree:" heading.
    tree = status.campaign_tree()[2:]
    if not tree:
        return "## Lineage\n\nNo candidates yet."
    return "## Lineage\n\n```text\n" + "\n".join(tree) + "\n```"


def _changes(campaign: Path, leaders: Sequence[SearchNode]) -> str:
    blocks = ["## What changed"]
    if not leaders:
        blocks.append("No scored candidate yet.")
    for node in leaders:
        stat = _diff_stat(campaign, node.parent_branch_name, node.branch_name)
        blocks.append(
            f"### Node {node.node_id}: `{node.branch_name}` against "
            f"`{node.parent_branch_name}`"
        )
        blocks.append(f"```text\n{stat}\n```" if stat else "No file changes.")
    return "\n\n".join(blocks)


def _diff_stat(campaign: Path, parent_branch: str, branch: str) -> str:
    result = subprocess.run(
        [
            "git", "--no-optional-locks", "-C", str(campaign),
            "diff", "--stat", "--no-color", parent_branch, branch, "--",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git diff {parent_branch} {branch} failed in {campaign}: "
            f"{result.stderr.strip()}"
        )
    return result.stdout.rstrip()


def _human_input(requests: Dict[int, Request]) -> str:
    if not requests:
        return "## Human input\n\nNo requests."
    rows = []
    for request in sorted(requests.values(), key=lambda request: request.id):
        if request.reply is None:
            reply = "waiting"
        else:
            reply = request.reply or "done, no note"
        rows.append([
            f"#{request.id}",
            str(request.node),
            f"`{request.key}`",
            request.fix,
            request.state,
            reply,
        ])
    return "## Human input\n\n" + _table(
        ["Request", "Node", "Needs", "Fix", "State", "Reply"], rows
    )


def _outcomes(nodes: Sequence[SearchNode], scored: int) -> str:
    return "\n".join([
        "## Outcomes",
        "",
        f"- **Candidates:** {len(nodes)}",
        f"- **Scored:** {scored}",
        f"- **Failed:** {sum(1 for node in nodes if node.had_error)}",
        "- **Integrity-flagged:** "
        f"{sum(1 for node in nodes if node.evaluation_integrity_error)}",
        f"- **Cost-refused:** {sum(1 for node in nodes if node.cost_refusal)}",
    ])


def _score(value: Optional[float]) -> str:
    return "unscored" if value is None else f"{value:.6g}"


def _table(header: List[str], rows: List[List[str]]) -> str:
    lines = [_row(header), "|" + "|".join("---" for _ in header) + "|"]
    lines.extend(_row(row) for row in rows)
    return "\n".join(lines)


def _row(cells: Sequence[str]) -> str:
    escaped = (
        " ".join(cell.split()).replace("|", "\\|") for cell in cells
    )
    return "| " + " | ".join(escaped) + " |"
