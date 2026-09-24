"""List the tool calls in a Claude Code stream-json log, in order, and print the final answer.

Shows whether the agent used the Skill tool on the entrypoint and which commands it ran.
Usage: python tools/tool_calls.py session.jsonl [--answer]
"""
import json
import sys


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    path, show_answer = sys.argv[1], "--answer" in sys.argv
    answer = ""
    n = 0
    raw = open(path, "rb").read()
    # Windows PowerShell 5.1 redirection (">") writes UTF-16; everything else writes UTF-8.
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16", errors="replace")
    else:
        text = raw.decode("utf-8-sig", errors="replace")
    if True:
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "system" and ev.get("subtype") == "init":
                skills = ev.get("skills") or ev.get("slash_commands") or []
                print(f"session init: model={ev.get('model')} tools={len(ev.get('tools') or [])} "
                      f"skills/commands seen={[s for s in skills if 'readiness' in str(s) or 'audit' in str(s)][:12]}")
            if ev.get("type") == "assistant":
                for block in ev.get("message", {}).get("content", []):
                    if block.get("type") == "tool_use":
                        n += 1
                        inp = block.get("input", {})
                        detail = inp.get("skill") or inp.get("command") or inp.get("file_path") or json.dumps(inp)[:120]
                        print(f"{n:>2}. {block.get('name')}: {str(detail)[:160]}")
            if ev.get("type") == "result":
                answer = ev.get("result") or ""
                print(f"result: subtype={ev.get('subtype')} turns={ev.get('num_turns')} "
                      f"duration={round((ev.get('duration_ms') or 0) / 1000)}s")
    if show_answer:
        print("\n----- final answer -----\n" + answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
