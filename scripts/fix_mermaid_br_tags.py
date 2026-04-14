#!/usr/bin/env python3
"""Fix <br/> tags inside Mermaid code blocks for Obsidian compatibility.

Obsidian's Mermaid renderer treats <br/> as unsupported HTML, showing
"Unsupported markdown: list" errors. This script replaces <br/> with
a space inside ```mermaid blocks only — regular HTML <br/> outside
mermaid blocks is left untouched.

Usage: python3 fix_mermaid_br.py <file1.md> [file2.md ...]
"""

import re
import sys

def fix_mermaid_br_tags(content: str) -> str:
    """Replace <br/> with space inside mermaid code blocks only."""
    # Split on mermaid fences. The pattern captures the full block
    # including the opening and closing ```.
    parts = re.split(r'(```mermaid\n.*?```)', content, flags=re.DOTALL)

    fixed_parts = []
    for part in parts:
        if part.startswith('```mermaid'):
            # Inside a mermaid block: replace all <br/> variants with space
            part = re.sub(r'<br\s*/?>', ' ', part)
        fixed_parts.append(part)

    return ''.join(fixed_parts)


def main():
    files = sys.argv[1:]
    if not files:
        print("Usage: fix_mermaid_br.py <file1.md> [file2.md ...]")
        sys.exit(1)

    total_fixed = 0
    for filepath in files:
        with open(filepath, 'r') as f:
            original = f.read()

        fixed = fix_mermaid_br_tags(original)

        if fixed != original:
            with open(filepath, 'w') as f:
                f.write(fixed)
            # Count how many replacements
            count = original.count('<br/>') + original.count('<br>') + original.count('<br />')
            fixed_count = fixed.count('<br/>') + fixed.count('<br>') + fixed.count('<br />')
            removed = count - fixed_count
            print(f"  Fixed {filepath} ({removed} <br/> tags removed from mermaid blocks)")
            total_fixed += 1
        # else: file had <br/> only outside mermaid blocks, skip silently

    print(f"\nDone. {total_fixed} files modified.")


if __name__ == '__main__':
    main()
