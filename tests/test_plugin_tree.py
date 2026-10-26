"""The plugin's tree (docs/plans/redesign/wp7-plugin.md, change 1): the
three manifests and the two marketplace files with the fields each host
reads, one MCP file per host naming the server `kapso` with that host's
command, the launcher's branches, and the hosts' own validators when
they are on PATH."""

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

import kapso

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"
LAUNCHER = PLUGIN / "scripts" / "kapso-mcp"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_manifests_name_the_plugin_and_their_hosts_mcp_file():
    claude = load(PLUGIN / ".claude-plugin" / "plugin.json")
    codex = load(PLUGIN / ".codex-plugin" / "plugin.json")
    cursor = load(PLUGIN / ".cursor-plugin" / "plugin.json")
    for manifest in (claude, codex, cursor):
        assert manifest["name"] == "kapso" and manifest["version"] == kapso.__version__
        assert manifest["description"] and manifest["author"]["name"] == "Leeroo"
    assert claude["mcpServers"] == "./hosts/claude/mcp.json" and claude["license"] == "MIT"
    assert codex["mcpServers"] == "./hosts/codex/mcp.json"
    assert cursor["mcpServers"] == "./hosts/cursor/mcp.json" and cursor["displayName"] == "Kapso"
    # Codex's listing: the display block, three starter prompts under 128 characters.
    interface = codex["interface"]
    assert interface["displayName"] == "Kapso" and interface["developerName"] == "Leeroo"
    assert set(interface["capabilities"]) <= {"Interactive", "Read", "Write"}
    assert len(interface["defaultPrompt"]) == 3 and all(len(prompt) <= 128 for prompt in interface["defaultPrompt"])
    # Every path a manifest names exists under the plugin root.
    for manifest in (claude, codex, cursor):
        for key in ("mcpServers", "skills", "commands"):
            if key in manifest and isinstance(manifest[key], str):
                assert (PLUGIN / manifest[key]).exists(), f"{key}: {manifest[key]}"


def test_each_hosts_mcp_file_names_the_server_kapso_with_the_command_that_host_can_run():
    """Claude Code expands the plugin-root variable and runs the launcher;
    Codex and Cursor take the command verbatim, so theirs is the installed
    `kapso-mcp` (the host facts, scripts/redesign/runs/wp7-hostfacts)."""
    claude = load(PLUGIN / "hosts" / "claude" / "mcp.json")["mcpServers"]["kapso"]
    codex = load(PLUGIN / "hosts" / "codex" / "mcp.json")["mcpServers"]["kapso"]
    cursor = load(PLUGIN / "hosts" / "cursor" / "mcp.json")["mcpServers"]["kapso"]
    assert claude["command"] == "${CLAUDE_PLUGIN_ROOT}/scripts/kapso-mcp" and claude["args"] == []
    assert codex["command"] == "kapso-mcp" and codex["default_tools_approval_mode"] == "approve"
    assert codex["startup_timeout_sec"] == 60
    assert cursor["command"] == "kapso-mcp"
    assert not (PLUGIN / ".mcp.json").exists()   # both hosts would read it, and they need different commands


def test_the_marketplace_files_offer_the_plugin_from_the_repository():
    claude = load(ROOT / ".claude-plugin" / "marketplace.json")
    codex = load(ROOT / ".agents" / "plugins" / "marketplace.json")
    assert claude["name"] == "kapso" and claude["description"] and claude["owner"]["name"] == "Leeroo"
    [entry] = claude["plugins"]
    assert entry["name"] == "kapso" and entry["source"] == "./plugin" and "version" not in entry   # the manifest's wins; one copy fewer
    assert codex["name"] == "kapso" and codex["interface"]["displayName"] == "Kapso"
    [entry] = codex["plugins"]
    assert entry["name"] == "kapso" and entry["source"] == {"source": "local", "path": "./plugin"}
    assert entry["policy"]["installation"] == "AVAILABLE" and entry["policy"]["authentication"] in ("ON_INSTALL", "ON_USE")


def test_the_launcher_pins_the_packages_version_and_is_executable():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert f'KAPSO_VERSION="{kapso.__version__}"' in text
    assert LAUNCHER.stat().st_mode & stat.S_IXUSR


def fake(bin_dir: Path, name: str, body: str) -> Path:
    """A fake executable; its shebang names bash by path, since the test's
    PATH holds the fakes alone."""
    path = bin_dir / name
    path.write_text(f"#!{shutil.which('bash')}\n" + body)
    path.chmod(0o755)
    return path


def launch(bin_dir: Path, *args: str):
    return subprocess.run(
        [shutil.which("bash"), str(LAUNCHER), *args], env={"PATH": str(bin_dir), "HOME": os.environ["HOME"]},
        capture_output=True, text=True,
    )


def test_the_launcher_runs_the_first_executable_found_and_never_a_second(tmp_path):
    seen = tmp_path / "seen"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    version = kapso.__version__
    # 1. The installed package wins, with the arguments passed through.
    fake(bin_dir, "kapso-mcp", f'echo "kapso-mcp $*" >> {seen}\n')
    fake(bin_dir, "uvx", f'echo "uvx $*" >> {seen}\n')
    assert launch(bin_dir, "--experience", "mine").returncode == 0
    assert seen.read_text() == "kapso-mcp --experience mine\n"
    # 2. One that fails is not followed by another: its exit code is the launcher's.
    fake(bin_dir, "kapso-mcp", f'echo "kapso-mcp $*" >> {seen}\necho "cannot serve" >&2\nexit 3\n')
    failed = launch(bin_dir)
    assert failed.returncode == 3 and failed.stderr.strip() == "cannot serve" and seen.read_text().count("uvx") == 0
    # 3. Without the package, uvx runs the pinned release.
    (bin_dir / "kapso-mcp").unlink()
    seen.unlink()
    assert launch(bin_dir, "--root", "/x").returncode == 0
    assert seen.read_text() == f"uvx --from leeroo-kapso=={version} kapso-mcp --root /x\n"
    # 4. Without uvx, pipx.
    (bin_dir / "uvx").unlink()
    seen.unlink()
    fake(bin_dir, "pipx", f'echo "pipx $*" >> {seen}\n')
    assert launch(bin_dir).returncode == 0
    assert seen.read_text() == f"pipx run --spec leeroo-kapso=={version} kapso-mcp\n"
    # 5. Nothing at all: one line naming the setup command, exit 1.
    (bin_dir / "pipx").unlink()
    nothing = launch(bin_dir)
    assert nothing.returncode == 1 and nothing.stdout == ""
    assert nothing.stderr.strip() == "kapso-mcp launcher: leeroo-kapso is not installed and neither uv nor pipx is on PATH; run /kapso:setup"


@pytest.mark.skipif(shutil.which("claude") is None, reason="the Claude Code CLI is not on PATH")
def test_the_hosts_own_validator_accepts_the_plugin_and_the_marketplace():
    for target in (PLUGIN, ROOT):
        checked = subprocess.run(
            ["claude", "plugin", "validate", str(target), "--strict", "--json"], capture_output=True, text=True,
        )
        report = json.loads(checked.stdout[checked.stdout.index("{"):])
        assert checked.returncode == 0 and report["success"], checked.stdout + checked.stderr
