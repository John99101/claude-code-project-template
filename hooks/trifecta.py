"""Lethal-trifecta check (Simon Willison): an agent that can (1) read private data, (2) read content an attacker can
write, and (3) send data out can be steered by a prompt injection into leaking that data.

This looks at the session's MCP servers (.mcp.json, ~/.claude.json) and allowed tools (permissions.allow in the
project, local and device settings) and sorts them into the three legs:
- data:      databases, Slack, Jira, GitHub (private repos), email, drives, reading .env
- untrusted: web fetch and search, browsers, issues and comments, docs from the web
- exfil:     outbound HTTP (curl, wget), posting to GitHub or Slack, browsers, email
The source code in the repo isn't counted as private data, or every setup would qualify.

session_start.py warns the user when all three are present. guard_bash.py then asks before commands that send
data out (curl -d, wget --post-data, gh api -X POST, nc, scp to a host). No credits. Turn off with "trifecta_check".
"""
import json
import os
import re

from cct_config import home_claude
import drift

LEGS = ("data", "untrusted", "exfil")
LABEL = {"data": "private data", "untrusted": "untrusted content", "exfil": "a way to send data out"}
KEYWORDS = [  # for MCP servers that aren't in the kit's catalog, matched against the server name
    (re.compile(r"postgres|mysql|maria|sqlite|mongo|redis|supabase|database|\bdb\b|bigquery|snowflake|neon", re.I),
     ["data"]),
    (re.compile(r"gmail|e-?mail|outlook|drive|notion|slack|jira|confluence|atlassian|linear|github|gitlab|sentry"
                r"|calendar|hubspot|salesforce|zendesk|intercom", re.I), ["data", "untrusted", "exfil"]),
    (re.compile(r"fetch|browser|playwright|puppeteer|chrome|search|brave|tavily|exa\b|firecrawl|scrap|web", re.I),
     ["untrusted", "exfil"]),
    (re.compile(r"context7|docs", re.I), ["untrusted"]),
]
TOOL_LEGS = [  # permission rules
    (re.compile(r"^WebFetch\b"), ["untrusted", "exfil"]),
    (re.compile(r"^WebSearch\b"), ["untrusted"]),
    (re.compile(r"^Bash\((curl|wget|http|https|xh|nc|ncat|netcat|scp|rsync|ssh)\b"), ["untrusted", "exfil"]),
    (re.compile(r"^Bash\(gh\b"), ["data", "untrusted", "exfil"]),
    (re.compile(r"^Read\([^)]*\.env"), ["data"]),
]
OUTBOUND_FLAGS = {
    "curl": {"-d", "--data", "--data-raw", "--data-binary", "--data-urlencode", "-F", "--form", "-T",
             "--upload-file", "--json"},
    "wget": {"--post-data", "--post-file", "--body-data", "--body-file"},
}


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def catalog(script_dir):
    """The kit's MCP catalog: next to the hooks in a project or plugin install, two levels up in a device install."""
    here = os.path.abspath(script_dir)
    for rel in (("..", "skills", "setup"), ("..", "..", "skills", "setup")):
        data = read_json(os.path.join(here, *rel, "mcp-catalog.json"))
        if data.get("servers"):
            return data["servers"]
    return {}


def same_dir(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def mcp_servers(proj):
    names = set(read_json(os.path.join(proj, ".mcp.json")).get("mcpServers") or {})
    user = read_json(os.path.join(os.path.expanduser("~"), ".claude.json"))
    names |= set(user.get("mcpServers") or {})
    for path, settings in (user.get("projects") or {}).items():
        if isinstance(settings, dict) and same_dir(path, proj):
            names |= set(settings.get("mcpServers") or {})
    return sorted(names)


def allowed_rules(proj):
    rules = []
    for path in (os.path.join(proj, ".claude", "settings.json"), os.path.join(proj, ".claude", "settings.local.json"),
                 os.path.join(home_claude(), "settings.json")):
        allow = (read_json(path).get("permissions") or {}).get("allow")
        rules += [r for r in allow or [] if isinstance(r, str)]
    return rules


def legs(proj, script_dir):
    """{leg: [sources]} for this project's setup."""
    known = catalog(script_dir)
    found = {leg: [] for leg in LEGS}
    for name in mcp_servers(proj):
        entry = known.get(name) if isinstance(known.get(name), dict) else None
        server_legs = entry.get("trifecta") if entry else None
        if not isinstance(server_legs, list):
            server_legs = next((found_legs for pattern, found_legs in KEYWORDS if pattern.search(name)), ["untrusted"])
        for leg in server_legs:
            if leg in found:
                found[leg].append(f"{name} (MCP)")
    for rule in allowed_rules(proj):
        for pattern, rule_legs in TOOL_LEGS:
            if pattern.search(rule):
                for leg in rule_legs:
                    found[leg].append(rule)
                break
    return found


def active(proj, script_dir):
    """The legs when all three are present, else None."""
    found = legs(proj, script_dir)
    return found if all(found[leg] for leg in LEGS) else None


def outbound(command):
    """A short description when the command sends data out of the machine, else None."""
    for seg in drift.segments(command, posix=True) or []:
        while seg and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", seg[0]):
            seg = seg[1:]
        if not seg:
            continue
        tool, args = os.path.basename(seg[0]).lower(), seg[1:]
        flags = {a.split("=", 1)[0] for a in args if a.startswith("-")}
        writes = any(a.upper() in ("POST", "PUT", "PATCH") for a in args)
        if tool in OUTBOUND_FLAGS and flags & OUTBOUND_FLAGS[tool]:
            return f"{tool} sends data"
        if tool == "curl" and writes:
            return "curl sends data"
        if tool in ("nc", "ncat", "netcat", "socat"):
            return f"{tool} opens a raw connection"
        if tool in ("scp", "rsync") and args and re.match(r"^[\w.-]+@?[\w.-]*:", args[-1]):
            return f"{tool} copies files to another host"
        if tool == "gh" and args[:1] == ["api"] and (flags & {"-f", "-F", "--field", "--raw-field", "--input"} or writes):
            return "gh api writes to GitHub"
    return None


def message(found):
    def names(leg):
        items = list(dict.fromkeys(found[leg]))
        return ", ".join(items[:3]) + (f" and {len(items) - 3} more" if len(items) > 3 else "")
    return ("[cct] This setup gives Claude all three parts of the \"lethal trifecta\": "
            + "; ".join(f"{LABEL[leg]} ({names(leg)})" for leg in LEGS)
            + ". A poisoned web page, issue or message could then make Claude send your data out. Safer: give data "
              "servers read-only, non-production logins; turn on web or browser servers only when needed (/mcp); "
              "remove outbound permissions you don't need. Outbound commands now need your OK. Turn this check off "
              "with \"trifecta_check\": false in .claude/cct.json.")
