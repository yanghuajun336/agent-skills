#!/usr/bin/env python3
# name=skill_l10n.py
# -*- coding: utf-8 -*-
"""
skill_l10n.py
Context-aware localization tool for Agent Skills (SKILL.md + references + scripts).
Usage:
  python skill_l10n.py <target_dir> <report_dir> [--src LANG] [--tgt LANG] [--mode replace|append] [--preserve-original-for-code yes|no]

Environment:
  DEEPSEEK_API_TOKEN  - required
  SKILL_L10N_VERIFY   - 'true' or 'false' (default 'false')
Dependencies:
  pip install openai httpx
"""
import os
import sys
import re
import json
import time
import argparse
import difflib
from pathlib import Path
from typing import Dict, Tuple, Optional

from openai import OpenAI
import httpx

# -----------------------
# Configuration defaults
# -----------------------
DEFAULT_MODEL = "deepseek-chat"
CACHE_TTL = 24 * 3600  # 1 day

# -----------------------
# Translator wrapper
# -----------------------
class SmartTranslator:
    def __init__(self, token_env="DEEPSEEK_API_TOKEN", verify_ssl: bool = False, model=DEFAULT_MODEL):
        self.token = os.getenv(token_env, "")
        if not self.token:
            raise ValueError(f"Please set environment variable {token_env}")
        self.verify = verify_ssl
        self._httpx_client = httpx.Client(verify=self.verify)
        self._client = OpenAI(base_url="https://api.deepseek.com/v1", api_key=self.token, http_client=self._httpx_client)
        self.model = model
        self.cache: Dict[str, Tuple[float, dict]] = {}

    def close(self):
        try:
            self._httpx_client.close()
        except Exception:
            pass

    def _cache_get(self, key: str) -> Optional[dict]:
        ent = self.cache.get(key)
        if not ent:
            return None
        ts, val = ent
        if time.time() - ts > CACHE_TTL:
            del self.cache[key]
            return None
        return val

    def _cache_set(self, key: str, val: dict):
        self.cache[key] = (time.time(), val)

    def decide_and_translate(self, paragraph: str, context: str = "", source_language="auto", target_language="zh") -> dict:
        """
        Ask model to decide whether to translate and return translation if should_translate.
        Return dict:
          { should_translate: bool, translated_text: str, reason: str }
        """
        key = f"decide::{source_language}::{target_language}::{paragraph}::ctx::{context}"
        cached = self._cache_get(key)
        if cached:
            return cached
        system_msg = (
            "You are a careful translator and content reviewer. "
            "Given a paragraph and surrounding context, return a JSON object with keys: "
            "should_translate (boolean), translated_text (string), reason (string). "
            "Do NOT translate code, CLI examples, file names, parameter names, or inline code. "
            "If you translate, preserve technical tokens and inline code unchanged."
        )
        user_msg = f"Context:\n{context}\n\nParagraph:\n{paragraph}\n\nSource: {source_language}\nTarget: {target_language}"
        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
            )
            raw = completion.choices[0].message.content.strip()
            # try extract JSON
            first = raw.find("{")
            last = raw.rfind("}")
            json_text = raw[first:last+1] if first != -1 and last != -1 else raw
            data = json.loads(json_text)
            result = {
                "should_translate": bool(data.get("should_translate")),
                "translated_text": data.get("translated_text", "") or "",
                "reason": data.get("reason", "") or "",
            }
        except Exception as e:
            result = {"should_translate": False, "translated_text": "", "reason": f"api_error:{e}"}
        self._cache_set(key, result)
        return result

# -----------------------
# File utilities
# -----------------------
MD_FENCE_RE = re.compile(r'```[\s\S]*?```', flags=re.MULTILINE)
INLINE_CODE_RE = re.compile(r'`[^`]+`')
FRONTMATTER_RE = re.compile(r'^(---\n[\s\S]*?\n---\n)', flags=re.MULTILINE)
COMMENT_PATTERNS = [
    re.compile(r'^[ \t]*#'),
    re.compile(r'^[ \t]*//'),
    re.compile(r'^[ \t]*/\*'),
    re.compile(r'^[ \t]*\*'),
    re.compile(r'^[ \t]*--'),
    re.compile(r'^[ \t]*;'),
    re.compile(r'^[ \t]*REM ', re.I),
    re.compile(r'^[ \t]*<!--'),
    re.compile(r'^[ \t]*"""'),
    re.compile(r"^[ \t]*'''"),
]
MD_SUFFIXES = {'.md'}
CODE_SUFFIXES = {'.py', '.js', '.ts', '.go', '.java', '.sh', '.yaml', '.yml'}
SPECIAL_FILES = {'Dockerfile', 'SKILL.md', 'SKILL.MD'}

def is_comment_line(line: str) -> bool:
    return any(pat.match(line) for pat in COMMENT_PATTERNS)

def safe_report_name(path: Path) -> str:
    s = str(path).lstrip(os.sep)
    return s.replace(os.sep, '-')

def write_diff_report(path: Path, orig_lines, new_lines, report_root: Path):
    report_root.mkdir(parents=True, exist_ok=True)
    rp = report_root / (safe_report_name(path) + ".diff")
    diff = difflib.unified_diff(orig_lines, new_lines, fromfile="original", tofile="localized", lineterm="")
    rp.write_text("\n".join(diff), encoding='utf-8')

# -----------------------
# Markdown: paragraph-level smart translation
# -----------------------
def process_markdown(path: Path, translator: SmartTranslator, report_root: Path, src='auto', tgt='zh', mode='replace'):
    text = path.read_text(encoding='utf-8')
    front = ""
    fm = FRONTMATTER_RE.match(text)
    if fm:
        front = fm.group(1)
        body = text[len(front):]
    else:
        body = text
    # hide code fences
    fences = {}
    def fence_repl(m):
        key = f"__FENCE_{len(fences)}__"
        fences[key] = m.group(0)
        return key
    body_ph = MD_FENCE_RE.sub(fence_repl, body)
    # split into paragraphs (keeping separators)
    parts = re.split(r'(\n\s*\n)', body_ph)
    new_parts = []
    for i, part in enumerate(parts):
        if part.strip() == "" or part.startswith("__FENCE_"):
            new_parts.append(part)
            continue
        # remove inline code
        inlines = INLINE_CODE_RE.findall(part)
        placeholders = {}
        for j, c in enumerate(inlines):
            ph = f"__INLINE_{j}__"
            placeholders[ph] = c
            part = part.replace(c, ph, 1)
        # context: prev + next non-empty
        prev_ctx = ""
        next_ctx = ""
        j = i-1
        while j >= 0:
            if parts[j].strip():
                prev_ctx = parts[j].strip()
                break
            j -= 1
        k = i+1
        while k < len(parts):
            if parts[k].strip():
                next_ctx = parts[k].strip()
                break
            k += 1
        ctx = "\n\n".join([c for c in (prev_ctx, next_ctx) if c])
        decision = translator.decide_and_translate(part.strip(), context=ctx, source_language=src, target_language=tgt)
        if decision.get("should_translate"):
            translated = decision.get("translated_text", "").strip()
            # restore inline placeholders
            for ph, c in placeholders.items():
                translated = translated.replace(ph, c)
            # how to insert depends on mode
            if mode == 'append':
                new_parts.append(part + "\n\n" + translated + "\n\n")
            else:
                new_parts.append(translated + "\n\n")
        else:
            new_parts.append(part)
    rebuilt = "".join(new_parts)
    # restore fences
    for k, v in fences.items():
        rebuilt = rebuilt.replace(k, v)
    final_text = front + rebuilt
    orig_lines = text.splitlines(keepends=True)
    new_lines = final_text.splitlines(keepends=True)
    if orig_lines != new_lines:
        path.write_text(final_text, encoding='utf-8')
        write_diff_report(path, orig_lines, new_lines, report_root)

# -----------------------
# Code files: translate comment lines only
# -----------------------
def process_code_file(path: Path, translator: SmartTranslator, report_root: Path, src='auto', tgt='zh', preserve_original_for_code=True):
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)
    new_lines = []
    modified = False
    for idx, line in enumerate(lines):
        if is_comment_line(line) and line.strip():
            prev_ctx = "".join(lines[max(0, idx-3):idx]).strip()
            next_ctx = "".join(lines[idx+1: idx+4]).strip()
            ctx = "\n".join([c for c in (prev_ctx, next_ctx) if c])
            decision = translator.decide_and_translate(line.strip(), context=ctx, source_language=src, target_language=tgt)
            if decision.get("should_translate"):
                translated = decision.get("translated_text", "").strip()
                # preserve indent and comment prefix
                m = re.match(r'^([ \t]*)([#\/\*]+[ \t]*)?(.*)$', line)
                indent = m.group(1) or ""
                prefix = m.group(2) or ""
                if preserve_original_for_code:
                    new_lines.append(line)
                    # add translated comment with same prefix
                    new_lines.append(f"{indent}{prefix}{translated}\n")
                else:
                    new_lines.append(f"{indent}{prefix}{translated}\n")
                modified = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    if modified:
        write_diff_report(path, lines, new_lines, report_root)
        path.write_text("".join(new_lines), encoding='utf-8')

# -----------------------
# Walk files
# -----------------------
def find_target_files(root: Path):
    files = []
    for p in root.rglob('*'):
        if p.is_file():
            if p.name in SPECIAL_FILES or p.suffix in MD_SUFFIXES or p.suffix in CODE_SUFFIXES:
                files.append(p)
    return files

# -----------------------
# CLI
# -----------------------
def parse_args():
    p = argparse.ArgumentParser(description="skill-L10n: context-aware localization for Agent skills")
    p.add_argument("target_dir", help="target directory to localize")
    p.add_argument("report_dir", help="directory to write diff reports")
    p.add_argument("--src", default="auto", help="source language (default auto)")
    p.add_argument("--tgt", default="zh", help="target language (default zh)")
    p.add_argument("--mode", choices=["replace", "append"], default=None, help="global mode for markdown. code files follow preserve flag")
    p.add_argument("--preserve-original-for-code", choices=["yes", "no"], default=None,
                   help="whether to keep original comments for code files (default yes)")
    return p.parse_args()

def main():
    args = parse_args()
    target = Path(args.target_dir)
    report = Path(args.report_dir)
    report.mkdir(parents=True, exist_ok=True)
    verify_env = os.getenv("SKILL_L10N_VERIFY", "false").lower() == "true"
    preserve_code = True if (args.preserve_original_for_code is None) else (args.preserve_original_for_code == "yes")
    markdown_mode = "replace" if args.mode is None else args.mode

    translator = SmartTranslator(verify_ssl=verify_env)
    try:
        files = find_target_files(target)
        for f in files:
            try:
                # treat SKILL.md or *.md as markdown
                if f.name.lower() == "skill.md" or f.suffix.lower() == ".md":
                    mode = markdown_mode
                    process_markdown(f, translator, report, src=args.src, tgt=args.tgt, mode=mode)
                else:
                    process_code_file(f, translator, report, src=args.src, tgt=args.tgt, preserve_original_for_code=preserve_code)
            except Exception as fe:
                print(f"[WARN] failed file {f}: {fe}", file=sys.stderr)
    finally:
        translator.close()

if __name__ == "__main__":
    main()
