"""Prove an unzipped marketplace folder is byte-for-byte the submitted Round 3 package.

Compares every file inside submission.zip with the same path in the folder, by SHA-256.
Fails (exit 1) if any submitted file is missing or differs. Files the run itself creates
(audit-output/, audit-precheck/, .claude/, __pycache__/) are listed as "added by the run", never compared,
because the engine's own outputs are expected; anything else extra is reported too.
Standard library only, so it runs anywhere the engine runs.

Usage: python verify_engine.py submission.zip <unzipped-marketplace-folder>
"""
import hashlib
import sys
import zipfile
from pathlib import Path

RUN_OUTPUTS = ("audit-output", "audit-precheck", "audit-replay", ".claude", "__pycache__")

# Files package_submission.py deliberately keeps OUT of the zip. Present in a git
# checkout, absent from the artifact, and not engine drift -- flagging them made
# the check report DIFFERS on a tree whose 155 engine files were all identical.
NOT_PACKAGED = (".gitattributes", ".gitignore", ".DS_Store")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    zip_path, folder = Path(sys.argv[1]), Path(sys.argv[2])
    zip_hash = sha256_bytes(zip_path.read_bytes())

    missing, differ, same = [], [], 0
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        for name in names:
            target = folder / name
            if not target.is_file():
                missing.append(name)
            elif sha256_bytes(target.read_bytes()) != sha256_bytes(z.read(name)):
                differ.append(name)
            else:
                same += 1

    # The REPLAY copies skills/ to .claude/skills so Claude Code can load the entrypoint with its
    # Skill tool. That copy must be byte-identical too, or the skill the agent reads would differ.
    copy_checked = 0
    if (folder / ".claude" / "skills").is_dir():
        with zipfile.ZipFile(zip_path) as z:
            for name in (n for n in names if n.startswith("skills/")):
                target = folder / ".claude" / name
                if not target.is_file():
                    missing.append(f".claude/{name}")
                elif sha256_bytes(target.read_bytes()) != sha256_bytes(z.read(name)):
                    differ.append(f".claude/{name}")
                else:
                    copy_checked += 1

    submitted = set(names) | {f".claude/{n}" for n in names if n.startswith("skills/")}
    extra = sorted(
        p.relative_to(folder).as_posix() for p in folder.rglob("*")
        if p.is_file() and p.relative_to(folder).as_posix() not in submitted
    )
    run_made = [e for e in extra if e.split("/")[0] in RUN_OUTPUTS or "/__pycache__/" in f"/{e}"]
    not_packaged = [e for e in extra if e.rsplit("/", 1)[-1] in NOT_PACKAGED]
    unexpected = [e for e in extra if e not in run_made and e not in not_packaged]

    print(f"submission.zip sha256 : {zip_hash}")
    print(f"files in submission   : {len(names)}")
    print(f"byte-identical        : {same}")
    if copy_checked:
        print(f".claude/skills copy   : {copy_checked} file(s) byte-identical to skills/")
    for label, items in (("MISSING", missing), ("DIFFERENT", differ), ("EXTRA (not from a run)", unexpected)):
        for item in items:
            print(f"{label:<22}: {item}")
    if run_made:
        kinds = sorted({"__pycache__" if "/__pycache__/" in f"/{e}" else e.split("/")[0] for e in run_made})
        print(f"added by the run      : {len(run_made)} file(s): {', '.join(kinds)}")
    ok = not missing and not differ and not unexpected
    print("RESULT                : " + ("ENGINE UNCHANGED" if ok else "ENGINE DIFFERS FROM THE SUBMISSION"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
