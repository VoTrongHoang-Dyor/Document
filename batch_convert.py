#!/usr/bin/env python3
"""
batch_convert.py — Convert multiple Markdown files to HTML and JSON.
Usage: python3 batch_convert.py
Output: <input_name>.html and <input_name>.json for each input MD file.
"""

import re
import os
import json
import sys
import time

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TARGET_FILES = [
    "Introduction.md",
    "Function.md",
    "Feature_Spec.md",
    "Design.md",
    "Core_Spec.md",
    "BusinessPlan.md",
]

TITLES = {
    "Introduction.md":  "TeraChat — System Introduction & Onboarding",
    "Function.md":      "TeraChat — Core Functions & Features",
    "Feature_Spec.md":  "TeraChat — Client Feature Specification",
    "Design.md":        "TeraChat — Product Requirements Document",
    "Core_Spec.md":     "TeraChat — Core Technical Specification",
    "BusinessPlan.md":  "TeraChat — Business Plan & GTM Strategy",
}

# ──────────────────────────────────────────
# HTML CONVERSION
# ──────────────────────────────────────────

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text

def parse_inline(text):
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code style="color:var(--accent-pink);background:rgba(255,255,255,0.1);padding:0.1rem 0.3rem;border-radius:4px;">\1</code>', text)
    text = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<img src="\2" alt="\1" style="max-width:100%;border-radius:8px;margin:1rem 0;">', text)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" style="color:var(--accent-blue);text-decoration:none;">\1</a>', text)
    return text

def parse_markdown(md_text):
    html_lines = []
    lines = md_text.split('\n')
    toc = []

    in_code_block = False
    code_block_content = []

    in_table = False
    table_header = []
    table_rows = []

    in_list = False
    list_type = None

    in_alert = False

    for line in lines:
        # --- Code Blocks ---
        if line.strip().startswith('```'):
            if in_code_block:
                escaped = '\n'.join(code_block_content)
                html_lines.append(
                    f'<div style="background:#0d0d0d;padding:1rem;border-radius:6px;overflow-x:auto;'
                    f'border:1px solid var(--border);margin:1rem 0;">'
                    f'<pre style="margin:0;color:#a5b4fc;font-size:0.85rem;white-space:pre-wrap;'
                    f'word-break:break-word;"><code>{escaped}</code></pre></div>'
                )
                in_code_block = False
                code_block_content = []
            else:
                in_code_block = True
            continue

        if in_code_block:
            safe = line.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            code_block_content.append(safe)
            continue

        # --- Tables ---
        if line.strip().startswith('|'):
            if not in_table:
                in_table = True
            if '---' in line and set(line.strip()) <= {'|', '-', ' ', ':'}:
                continue
            row = [c.strip() for c in line.strip('|').split('|')]
            if not table_header:
                table_header = row
            else:
                table_rows.append(row)
            continue
        elif in_table:
            in_table = False
            html_lines.append('<div class="comparison-table"><table>')
            html_lines.append('<thead><tr>')
            for h in table_header:
                html_lines.append(f'<th>{parse_inline(h)}</th>')
            html_lines.append('</tr></thead><tbody>')
            for row in table_rows:
                html_lines.append('<tr>')
                for cell in row:
                    html_lines.append(f'<td>{parse_inline(cell)}</td>')
                html_lines.append('</tr>')
            html_lines.append('</tbody></table></div>')
            table_header = []
            table_rows = []
            if not line.strip():
                continue

        # --- GitHub Alerts / Blockquotes ---
        if line.strip().startswith('>'):
            content = line.strip().lstrip('>').strip()
            if content.startswith('[!WARNING]'):
                if in_alert: html_lines.append('</div>')
                html_lines.append('<div class="tech-box" style="border-color:var(--warning);">')
                html_lines.append('<div class="tech-header" style="color:var(--warning);">⚠️ WARNING</div>')
                in_alert = True
                continue
            elif content.startswith('[!IMPORTANT]'):
                if in_alert: html_lines.append('</div>')
                html_lines.append('<div class="tech-box" style="border-color:var(--accent-purple);">')
                html_lines.append('<div class="tech-header" style="color:var(--accent-purple);">🔺 IMPORTANT</div>')
                in_alert = True
                continue
            elif content.startswith('[!NOTE]') or content.startswith('[!TIP]'):
                if in_alert: html_lines.append('</div>')
                html_lines.append('<div class="tech-box">')
                html_lines.append('<div class="tech-header" style="color:var(--accent-blue);">📝 NOTE</div>')
                in_alert = True
                continue
            elif content == '':
                if in_alert:
                    html_lines.append('</div>')
                    in_alert = False
                continue
            else:
                if in_alert:
                    html_lines.append(f'<p>{parse_inline(content)}</p>')
                else:
                    html_lines.append(f'<p style="padding-left:1rem;border-left:4px solid var(--border);color:var(--text-secondary);">{parse_inline(content)}</p>')
                continue

        if in_alert and not line.strip().startswith('>'):
            html_lines.append('</div>')
            in_alert = False

        # --- Headers ---
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if header_match:
            if in_list:
                html_lines.append(f'</{list_type}>')
                in_list = False
            level = len(header_match.group(1))
            text = header_match.group(2).strip()
            anchor = slugify(text)
            toc.append({'level': level, 'text': text, 'anchor': anchor})
            html_lines.append(f'<h{level} id="{anchor}">{text}</h{level}>')
            continue

        # --- Lists ---
        list_match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.+)$', line)
        if list_match:
            content = list_match.group(3)
            current_type = 'ol' if list_match.group(2)[0].isdigit() else 'ul'
            if not in_list:
                in_list = True
                list_type = current_type
                html_lines.append(f'<{list_type}>')
            elif list_type != current_type:
                html_lines.append(f'</{list_type}>')
                list_type = current_type
                html_lines.append(f'<{list_type}>')
            html_lines.append(f'<li>{parse_inline(content)}</li>')
            continue
        elif in_list:
            in_list = False
            html_lines.append(f'</{list_type}>')

        # --- Horizontal Rules ---
        if re.match(r'^---+$', line.strip()):
            html_lines.append('<hr style="border:0;border-top:1px solid var(--border);margin:2rem 0;">')
            continue

        # --- Paragraphs ---
        if line.strip():
            html_lines.append(f'<p>{parse_inline(line)}</p>')
        else:
            if in_list:
                in_list = False
                html_lines.append(f'</{list_type}>')

    if in_table:
        html_lines.append('</tbody></table></div>')
    if in_list:
        html_lines.append(f'</{list_type}>')
    if in_alert:
        html_lines.append('</div>')

    html_output = '\n'.join(html_lines)
    
    # Platform Architecture Properties (Non-tabular specific formatting)
    def parse_platforms(match):
        text = match.group(1)
        stripped = re.sub(r'[\s\uFE0F]', '', text)
        if not stripped or not all(c in '📱💻🖥☁🗄' for c in stripped):
            return match.group(0)
            
        res = []
        if '📱' in text: res.append('<span class="platform-chip">📱 Mobile</span>')
        if '💻' in text: res.append('<span class="platform-chip">💻 Laptop</span>')
        if '🖥' in text: res.append('<span class="platform-chip">🖥 Desktop</span>')
        if '☁' in text: res.append('<span class="platform-chip">☁ VPS Cluster</span>')
        if '🗄' in text: res.append('<span class="platform-chip">🗄 Server Vật Lý</span>')
        
        if res:
            return '<div class="platform-list">' + ' &middot; '.join(res) + '</div>'
        return match.group(0)

    html_output = re.sub(r'<p>(.*?)</p>', parse_platforms, html_output)

    html_output = re.sub(r'<li>\s*<strong>Priority:</strong>\s*(Core|Recommended|Optional)\s*</li>', 
                  r'<li class="tech-prop" style="list-style:none; margin-top:0.5rem;"><span class="prop-label">Priority:</span> <span class="badge-prop \1">\1</span></li>', html_output, flags=re.IGNORECASE)
    html_output = re.sub(r'<li>\s*<strong>Cross-platform:</strong>\s*(Có|Không)\s*</li>', 
                  lambda m: f'<li class="tech-prop" style="list-style:none;"><span class="prop-label">Cross-platform:</span> <span class="badge-prop {"yes" if m.group(1).lower()=="có" else "no"}">{m.group(1)}</span></li>', html_output, flags=re.IGNORECASE)
    html_output = re.sub(r'<li>\s*<strong>Lý do phù hợp:</strong>\s*(.+?)</li>', 
                  r'<li class="tech-prop" style="list-style:none;align-items:flex-start;"><span class="prop-label" style="color:var(--success);">Lý do phù hợp:</span> <span style="flex:1;">\1</span></li>', html_output, flags=re.DOTALL)
    html_output = re.sub(r'<li>\s*<strong>Hạn chế:</strong>\s*(.+?)</li>', 
                  r'<li class="tech-prop" style="list-style:none;align-items:flex-start;"><span class="prop-label" style="color:var(--warning);">Hạn chế:</span> <span style="flex:1;opacity:0.9;">\1</span></li>', html_output, flags=re.DOTALL)

    html_output = html_output.replace('[NEW]', '<span class="badge badge-success">NEW</span>')

    return html_output, toc


def extract_css(html_path):
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
            if match:
                return match.group(1)
    except FileNotFoundError:
        pass
    return ""


def build_html(md_path, output_path, title, css):
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    html_content, toc = parse_markdown(md_text)

    toc_html = '<div class="nav-header">Table of Contents</div>'
    for item in toc:
        if item['level'] <= 3:
            indent = 'padding-left:0.8rem;' if item['level'] > 1 else ''
            toc_html += f'<a href="#{item["anchor"]}" class="nav-link" style="{indent}">{item["text"]}</a>\n'

    search_css = """
        /* Search Box */
        .search-container {
            position: relative;
            margin-bottom: 1.5rem;
        }
        .search-input {
            width: 100%;
            padding: 0.6rem 0.8rem 0.6rem 2.2rem;
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 0.85rem;
            font-family: var(--font-main, system-ui);
            outline: none;
            transition: all 0.2s;
        }
        .search-input::placeholder {
            color: var(--text-secondary);
            opacity: 0.6;
        }
        .search-input:focus {
            border-color: var(--accent-blue);
            background: rgba(255,255,255,0.08);
            box-shadow: 0 0 0 3px rgba(56,189,248,0.1);
        }
        .search-icon {
            position: absolute;
            left: 0.7rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-secondary);
            font-size: 0.85rem;
            pointer-events: none;
        }
        .search-shortcut {
            position: absolute;
            right: 0.5rem;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(255,255,255,0.08);
            color: var(--text-secondary);
            font-size: 0.65rem;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            border: 1px solid var(--border);
            pointer-events: none;
        }
        .nav-link.search-hidden {
            display: none !important;
        }
        .search-no-results {
            color: var(--text-secondary);
            font-size: 0.8rem;
            padding: 0.5rem 0.8rem;
            opacity: 0.6;
            display: none;
        }

        /* Tech Properties */
        .tech-prop { font-size: 0.85rem; margin-bottom: 0.3rem; display: flex; align-items: center; }
        .tech-prop .prop-label { font-weight: 600; color: var(--text-secondary); width: 130px; }
        
        .badge-prop {
            display: inline-flex;
            align-items: center;
            padding: 0.15rem 0.5rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .badge-prop.core { background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239,68,68,0.3); }
        .badge-prop.recommended { background: rgba(59, 130, 246, 0.15); color: #93c5fd; border: 1px solid rgba(59,130,246,0.3); }
        .badge-prop.optional { background: rgba(156, 163, 175, 0.15); color: #d1d5db; border: 1px solid rgba(156,163,175,0.3); }
        .badge-prop.yes { background: rgba(74, 222, 128, 0.15); color: #86efac; border: 1px solid rgba(74,222,128,0.3); }
        .badge-prop.no { background: rgba(244, 114, 182, 0.15); color: #f9a8d4; border: 1px solid rgba(244,114,182,0.3); }

        /* Platform Chips */
        .platform-list {
            margin: 0.8rem 0;
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            align-items: center;
            color: var(--text-secondary);
        }
        .platform-chip {
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--text-primary);
        }
    """

    final_html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
    {css}
    {search_css}
    </style>
</head>
<body>

<nav class="sidebar">
    <a href="#" class="brand">TeraChat <span>{title.split("—")[-1].strip()}</span></a>

    <div class="search-container">
        <span class="search-icon">🔍</span>
        <input type="text" class="search-input" id="tocSearch" placeholder="Tra cứu mục lục..." autocomplete="off">
        <span class="search-shortcut">Ctrl+K</span>
    </div>

    {toc_html}
    <div class="search-no-results" id="searchNoResults">Không tìm thấy kết quả.</div>
</nav>

<div class="main">
    {html_content}

    <div style="margin-top:4rem;padding-top:2rem;border-top:1px solid var(--border);
                color:var(--text-secondary);font-size:0.9rem;text-align:center;">
        <p>TeraChat Enterprise OS &copy; 2026</p>
    </div>
</div>

<script>
(function() {{
    const searchInput = document.getElementById('tocSearch');
    const noResults = document.getElementById('searchNoResults');
    const navLinks = document.querySelectorAll('.sidebar .nav-link');

    // Filter TOC on input
    searchInput.addEventListener('input', function() {{
        const query = this.value.toLowerCase().trim();
        let visibleCount = 0;

        navLinks.forEach(function(link) {{
            if (!query) {{
                link.classList.remove('search-hidden');
                visibleCount++;
            }} else {{
                const text = link.textContent.toLowerCase();
                if (text.includes(query)) {{
                    link.classList.remove('search-hidden');
                    visibleCount++;
                }} else {{
                    link.classList.add('search-hidden');
                }}
            }}
        }});

        noResults.style.display = (query && visibleCount === 0) ? 'block' : 'none';
    }});

    // Ctrl+K shortcut
    document.addEventListener('keydown', function(e) {{
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {{
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        }}
        if (e.key === 'Escape' && document.activeElement === searchInput) {{
            searchInput.value = '';
            searchInput.dispatchEvent(new Event('input'));
            searchInput.blur();
        }}
    }});
}})();
</script>

</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)

    print(f"  ✅ HTML → {os.path.basename(output_path)}")


# ──────────────────────────────────────────
# JSON CONVERSION
# ──────────────────────────────────────────

def md_to_json(md_text, title):
    """
    Parse Markdown into structured JSON:
    {
      "title": "...",
      "sections": [
        {
          "id": "...",
          "level": 1,
          "heading": "...",
          "content_blocks": [
            {"type": "paragraph"|"table"|"code"|"list"|"blockquote", "data": ...}
          ],
          "subsections": [...]
        }
      ]
    }
    """
    lines = md_text.split('\n')
    result = {"title": title, "generated_at": "2026-02-23", "sections": []}

    section_stack = []      # stack of (level, section_dict)
    current_blocks = []     # current content_blocks being filled

    in_code = False
    code_lang = ""
    code_lines = []

    in_table = False
    table_header = []
    table_rows = []

    list_items = []
    in_list = False

    def flush_list():
        nonlocal list_items, in_list
        if list_items:
            current_blocks.append({"type": "list", "data": list_items[:]})
            list_items = []
            in_list = False

    def flush_table():
        nonlocal in_table, table_header, table_rows
        if table_header:
            current_blocks.append({
                "type": "table",
                "headers": table_header[:],
                "rows": table_rows[:]
            })
        in_table = False
        table_header = []
        table_rows = []

    def get_current_blocks():
        # Returns the blocks list for the deepest active section
        if section_stack:
            return section_stack[-1][1]['content_blocks']
        return result['sections']

    def push_section(level, heading):
        flush_list()
        flush_table()
        section = {
            "id": slugify(heading),
            "level": level,
            "heading": heading,
            "content_blocks": [],
            "subsections": []
        }
        # Pop sections that are same or deeper level
        while section_stack and section_stack[-1][0] >= level:
            section_stack.pop()

        if section_stack:
            section_stack[-1][1]['subsections'].append(section)
        else:
            result['sections'].append(section)

        section_stack.append((level, section))
        return section['content_blocks']

    blocks = result['sections']  # Will be overridden once first heading seen

    for line in lines:
        # Code block
        if line.strip().startswith('```'):
            if in_code:
                # close code
                cb = get_current_blocks() if section_stack else []
                if section_stack:
                    section_stack[-1][1]['content_blocks'].append({
                        "type": "code",
                        "language": code_lang,
                        "code": '\n'.join(code_lines)
                    })
                in_code = False
                code_lines = []
                code_lang = ""
            else:
                in_code = True
                code_lang = line.strip().replace('```', '').strip()
            continue

        if in_code:
            code_lines.append(line)
            continue

        # Table
        if line.strip().startswith('|'):
            if not in_table:
                in_table = True
            if '---' in line and set(line.strip()) <= {'|', '-', ' ', ':'}:
                continue
            row = [c.strip() for c in line.strip('|').split('|')]
            if not table_header:
                table_header = row
            else:
                table_rows.append(row)
            continue
        elif in_table:
            if section_stack:
                section_stack[-1][1]['content_blocks'].append({
                    "type": "table",
                    "headers": table_header[:],
                    "rows": [r[:] for r in table_rows]
                })
            in_table = False
            table_header = []
            table_rows = []
            if not line.strip():
                continue

        # Blockquote
        if line.strip().startswith('>'):
            flush_list()
            content = line.strip().lstrip('>').strip()
            alert_type = "note"
            if content.startswith('[!WARNING]'): alert_type = "warning"; content = ""
            elif content.startswith('[!IMPORTANT]'): alert_type = "important"; content = ""
            elif content.startswith('[!NOTE]') or content.startswith('[!TIP]'): alert_type = "note"; content = ""
            if content and section_stack:
                # append to last blockquote or create new one
                cb = section_stack[-1][1]['content_blocks']
                if cb and cb[-1].get('type') == 'blockquote':
                    cb[-1]['lines'].append(content)
                else:
                    cb.append({"type": "blockquote", "alert_type": alert_type, "lines": [content] if content else []})
            continue

        # Header
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if header_match:
            flush_list()
            flush_table()
            level = len(header_match.group(1))
            heading = header_match.group(2).strip()
            push_section(level, heading)
            continue

        # List
        list_match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.+)$', line)
        if list_match:
            content = list_match.group(3).strip()
            # Strip inline markdown
            content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
            content = re.sub(r'\*(.+?)\*', r'\1', content)
            content = re.sub(r'`(.+?)`', r'\1', content)
            if section_stack:
                cb = section_stack[-1][1]['content_blocks']
                if cb and cb[-1].get('type') == 'list':
                    cb[-1]['data'].append(content)
                else:
                    cb.append({"type": "list", "data": [content]})
            continue

        # HR
        if re.match(r'^---+$', line.strip()):
            continue

        # Paragraph
        if line.strip() and section_stack:
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', line.strip())
            clean = re.sub(r'\*(.+?)\*', r'\1', clean)
            clean = re.sub(r'`(.+?)`', r'\1', clean)
            section_stack[-1][1]['content_blocks'].append({"type": "paragraph", "text": clean})

    # Final flush
    if in_table and section_stack:
        section_stack[-1][1]['content_blocks'].append({
            "type": "table",
            "headers": table_header[:],
            "rows": [r[:] for r in table_rows]
        })

    return result


def build_json(md_path, output_path, title):
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    data = md_to_json(md_text, title)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  ✅ JSON → {os.path.basename(output_path)}")


# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────

def run_conversion():
    template_path = os.path.join(BASE_DIR, "TeraChat-V0.2.1-TechSpec.html")
    css = extract_css(template_path)
    if not css:
        # Full fallback CSS (matching TeraChat-V0.2.1-TechSpec.html design)
        css = """
        :root {
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --bg-sidebar: #020617;
            --text-primary: #e2e8f0;
            --text-secondary: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-purple: #818cf8;
            --accent-pink: #f472b6;
            --success: #4ade80;
            --warning: #fbbf24;
            --danger: #ef4444;
            --info: #3b82f6;
            --border: #334155;
            --font-main: 'Inter', system-ui, -apple-system, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }

        * { box-sizing: border-box; }

        body {
            background-color: var(--bg-dark);
            color: var(--text-primary);
            font-family: var(--font-main);
            margin: 0;
            line-height: 1.6;
            overflow-x: hidden;
            width: 100%;
            display: grid;
            grid-template-columns: 280px minmax(0, 1fr);
            min-height: 100vh;
        }

        .sidebar {
            background-color: var(--bg-sidebar);
            border-right: 1px solid var(--border);
            height: 100vh;
            padding: 2rem 1rem;
            position: sticky;
            top: 0;
            overflow-y: auto;
            z-index: 100;
        }

        .brand {
            font-size: 1.4rem;
            font-weight: 800;
            color: var(--text-primary);
            margin-bottom: 2rem;
            display: block;
            letter-spacing: -0.5px;
            text-decoration: none;
        }
        .brand span { color: var(--accent-purple); }

        .nav-header {
            font-size: 0.75rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            font-weight: 700;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
            padding-left: 0.8rem;
        }

        .nav-link {
            display: block;
            color: var(--text-secondary);
            text-decoration: none;
            padding: 0.6rem 0.8rem;
            border-radius: 6px;
            margin-bottom: 0.25rem;
            font-size: 0.9rem;
            transition: all 0.2s;
            border-left: 2px solid transparent;
        }

        .nav-link:hover, .nav-link.active {
            color: var(--accent-blue);
            background: rgba(56, 189, 248, 0.05);
            border-left-color: var(--accent-blue);
        }

        .main {
            padding: 4rem 4rem;
            max-width: 100%;
            width: 100%;
            margin: 0 auto;
        }

        h1 { font-size: 2.5rem; margin-top: 0; border-bottom: 1px solid var(--border); padding-bottom: 1rem; color: #fff; }
        h2 { font-size: 1.8rem; color: var(--accent-purple); margin-top: 3rem; display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
        h3 { font-size: 1.25rem; color: var(--text-primary); margin-top: 2rem; border-left: 4px solid var(--accent-blue); padding-left: 1rem; }

        p, ul { color: var(--text-secondary); margin-bottom: 1rem; }
        li { margin-bottom: 0.5rem; }

        .scenario-card {
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1.5rem 0;
            position: relative;
            overflow: hidden;
            max-width: 100%;
        }

        .scenario-card::before {
            content: "USER EXPERIENCE";
            position: absolute;
            top: 0; right: 0;
            background: var(--border);
            color: var(--text-secondary);
            font-size: 0.65rem;
            font-weight: bold;
            padding: 0.25rem 0.75rem;
            border-bottom-left-radius: 8px;
        }

        .scenario-step {
            display: grid;
            grid-template-columns: 120px 1fr;
            gap: 1.5rem;
            margin-bottom: 1rem;
            align-items: baseline;
        }

        @media (max-width: 768px) {
            .scenario-step { grid-template-columns: 1fr; gap: 0.5rem; }
        }

        .step-label {
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--accent-blue);
            text-transform: uppercase;
            text-align: right;
        }

        .tech-box {
            background: #0f1219;
            border: 1px solid #2d3748;
            border-radius: 8px;
            padding: 1.5rem;
            margin-top: 1rem;
            font-family: var(--font-mono);
            font-size: 0.9rem;
            max-width: 100%;
            overflow-x: auto;
        }

        .tech-header {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
            color: var(--accent-pink);
            font-weight: bold;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .comparison-table {
            width: 100%;
            overflow-x: auto;
            margin: 1rem 0;
            display: block;
            -webkit-overflow-scrolling: touch;
        }
        .comparison-table table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
            min-width: 600px;
        }

        .comparison-table th { text-align: left; color: var(--text-secondary); border-bottom: 1px solid var(--border); padding: 0.5rem; }
        .comparison-table td { padding: 0.75rem 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .old-way { color: var(--danger); text-decoration: line-through; opacity: 0.7; }
        .new-way { color: var(--success); font-weight: 500; }

        .badge {
            display: inline-flex;
            align-items: center;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-left: 0.5rem;
            background: rgba(255,255,255,0.1);
        }

        .badge-success { color: var(--success); background: rgba(74, 222, 128, 0.1); }
        .badge-danger { color: var(--danger); background: rgba(239, 68, 68, 0.1); }
        .badge-warning { color: var(--warning); background: rgba(251, 191, 36, 0.1); }
        .badge-info { color: var(--info); background: rgba(59, 130, 246, 0.1); }

        pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-x: auto;
            max-width: 100%;
        }

        code { background: rgba(255,255,255,0.08); padding: 0.1rem 0.3rem; border-radius: 4px; }

        @media (max-width: 900px) {
            body {
                grid-template-columns: 1fr;
            }
            .sidebar {
                width: 100%;
                height: auto;
                position: relative;
                border-right: none;
                border-bottom: 1px solid var(--border);
                padding: 1rem;
            }
            .main {
                padding: 2rem 1.5rem;
                width: 100%;
            }
            h1 { font-size: 1.8rem; }
            h2 { font-size: 1.5rem; margin-top: 2rem; }
        }
        """

    for fname in TARGET_FILES:
        md_path = os.path.join(BASE_DIR, fname)
        base = os.path.splitext(fname)[0]
        html_out = os.path.join(BASE_DIR, f"{base}.html")
        json_out = os.path.join(BASE_DIR, f"{base}.json")
        title = TITLES.get(fname, base)

        if not os.path.exists(md_path):
             continue

        print(f"📄 {fname}")
        build_html(md_path, html_out, title, css)
        build_json(md_path, json_out, title)

def watch_mode():
    print(f"\n👀 Đang theo dõi sự thay đổi của {len(TARGET_FILES)} files...")
    print("Nhấn Ctrl+C để dừng.\n")
    
    last_mtimes = {}
    for fname in TARGET_FILES:
        path = os.path.join(BASE_DIR, fname)
        if os.path.exists(path):
            last_mtimes[fname] = os.path.getmtime(path)
            
    try:
        while True:
            time.sleep(1)
            changed = False
            for fname in TARGET_FILES:
                path = os.path.join(BASE_DIR, fname)
                if os.path.exists(path):
                    current_mtime = os.path.getmtime(path)
                    if fname not in last_mtimes or current_mtime > last_mtimes[fname]:
                        print(f"📝 Phát hiện thay đổi: {fname}")
                        last_mtimes[fname] = current_mtime
                        changed = True
            
            if changed:
                print("🔄 Đang đồng bộ HTML và JSON...")
                run_conversion()
                print("✅ Đồng bộ hoàn tất. Tiếp tục theo dõi...\n")
                
    except KeyboardInterrupt:
        print("\n🛑 Đã dừng auto-sync.")

def main():
    if "--watch" in sys.argv:
        watch_mode()
    else:
        print(f"\nConverting {len(TARGET_FILES)} files in {BASE_DIR}...\n")
        run_conversion()
        print("\n✅ All done!")

if __name__ == "__main__":
    main()
