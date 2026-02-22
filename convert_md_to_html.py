import re
import os
import sys

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text

def parse_markdown(md_text):
    html_lines = []
    lines = md_text.split('\n')
    toc = []
    
    in_code_block = False
    code_block_lang = ""
    code_block_content = []
    
    in_table = False
    table_header = []
    table_rows = []
    
    in_list = False
    list_type = None # 'ul' or 'ol'
    
    for line in lines:
        # --- Code Blocks ---
        if line.strip().startswith('```'):
            if in_code_block:
                # End code block
                html_lines.append(f'<div style="background: #000; padding: 1rem; border-radius: 6px; overflow-x: auto; border: 1px solid var(--border); margin: 1rem 0;"><pre style="margin: 0; color: #a5b4fc; font-size: 0.85rem;"><code>{chr(10).join(code_block_content)}</code></pre></div>')
                in_code_block = False
                code_block_content = []
            else:
                # Start code block
                in_code_block = True
                code_block_lang = line.strip().replace('```', '')
            continue
            
        if in_code_block:
            # Escape HTML in code blocks
            safe_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            code_block_content.append(safe_line)
            continue

        # --- Tables ---
        if line.strip().startswith('|'):
            if not in_table:
                in_table = True
                # Check if it's a separator line (e.g., |---|---|)
                if '---' in line:
                     continue # Skip separator line if it's the first line (unlikely but possible)
                
            if '---' in line and set(line.strip()) <= {'|', '-', ' ', ':'}:
                continue # Skip separator line
            
            row = [c.strip() for c in line.strip('|').split('|')]
            if not table_header:
                table_header = row
            else:
                table_rows.append(row)
            continue
        elif in_table:
            # End of table
            in_table = False
            html_lines.append('<div class="comparison-table"><table>')
            # Header
            html_lines.append('<thead><tr>')
            for h in table_header:
                 html_lines.append(f'<th>{parse_inline(h)}</th>')
            html_lines.append('</tr></thead>')
            # Body
            html_lines.append('<tbody>')
            for row in table_rows:
                html_lines.append('<tr>')
                for cell in row:
                     html_lines.append(f'<td>{parse_inline(cell)}</td>')
                html_lines.append('</tr>')
            html_lines.append('</tbody></table></div>')
            table_header = []
            table_rows = []
            # Continue processing this line as normal text if it's not empty, otherwise just loop
            if not line.strip():
                continue

        # --- GitHub Alerts / Blockquotes ---
        if line.strip().startswith('>'):
            content = line.strip().lstrip('>').strip()
            if content.startswith('[!WARNING]'):
                html_lines.append('<div class="tech-box" style="border-color: var(--warning);">')
                html_lines.append(f'<div class="tech-header" style="color: var(--warning);">WARNING</div>')
                continue
            elif content.startswith('[!IMPORTANT]'):
                html_lines.append('<div class="tech-box" style="border-color: var(--accent-purple);">')
                html_lines.append(f'<div class="tech-header" style="color: var(--accent-purple);">IMPORTANT</div>')
                continue
            elif content.startswith('[!NOTE]') or content.startswith('[!TIP]'):
                html_lines.append('<div class="tech-box">')
                html_lines.append(f'<div class="tech-header" style="color: var(--accent-blue);">NOTE</div>')
                continue
            elif content.startswith('[!Bc]'): # Handle block close if we want to be fancy, otherwise just treat as text
                 pass
            
            # Standard blockquote line
            html_lines.append(f'<p style="padding-left: 1rem; border-left: 4px solid var(--border); color: var(--text-secondary);">{parse_inline(content)}</p>')
            # If we recently opened a div for alert, close it? 
            # Simple parser limitation: alerts in MD usually end with a blank line. 
            # We'll rely on "Paragraph" logic to close divs or just leave them open until end of section for simplicity
            # Actually, let's close the div if we hit a blank line later.
            continue


        # --- Headers ---
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if header_match:
            level = len(header_match.group(1))
            text = header_match.group(2).strip()
            anchor = slugify(text)
            toc.append({'level': level, 'text': text, 'anchor': anchor})
            
            html_lines.append(f'<h{level} id="{anchor}">{text}</h{level}>')
            continue

        # --- Lists ---
        list_match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.+)$', line)
        if list_match:
            indent = len(list_match.group(1))
            separator = list_match.group(2)
            content = list_match.group(3)
            current_type = 'ol' if separator[0].isdigit() else 'ul'
            
            if not in_list:
                in_list = True
                list_type = current_type
                html_lines.append(f'<{list_type}>')
            elif list_type != current_type:
                 # Switch list type (nested lists strictly not supported in this simple parser, but we handle the switch)
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
            html_lines.append('<hr style="border: 0; border-top: 1px solid var(--border); margin: 2rem 0;">')
            continue

        # --- Paragraphs ---
        if line.strip():
            # Check if we assume it is a paragraph
            # (Close any open blockquotes or divs if we were smarter, but simplistic approach:)
            if parser_state_check_closing(line): 
                 pass # Placeholder for closing logic

            html_lines.append(f'<p>{parse_inline(line)}</p>')
        else:
            # Blank line - might match end of block
             if in_list:
                in_list = False
                html_lines.append(f'</{list_type}>')
             # Close alert divs? We'll leave them open if they are blockquotes, but standard p tags handle most spacing.
             # Ideally we'd track "in_alert" state.
             pass

    # Flush remaining
    if in_table:
        # (Duplicate close logic if file ends with table)
        html_lines.append('</tbody></table></div>')

    return '\n'.join(html_lines), toc

def parser_state_check_closing(line):
    # Dummy function for complex state
    return False

def parse_inline(text):
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Inline Code
    text = re.sub(r'`(.+?)`', r'<code style="color: var(--accent-pink); background: rgba(255,255,255,0.1); padding: 0.1rem 0.3rem; border-radius: 4px;">\1</code>', text)
    # Images with badges class hack (e.g. ![Deep Dive: Federated Private Clusters](badge)) - specific project requirement?
    # No, standard image: ![alt](src)
    text = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<img src="\2" alt="\1" style="max-width: 100%; border-radius: 8px; margin: 1rem 0;">', text)
    # Links: [text](href)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" style="color: var(--accent-blue); text-decoration: none;">\1</a>', text)
    return text

def extract_style(html_path):
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
            if match:
                return match.group(1)
    except FileNotFoundError:
        print("Warning: Template HTML not found, using default styles.")
    return ""

def main():
    base_dir = "/Users/hoang_dyor_i/Code_Projects/DocumentTeraChat"
    md_path = os.path.join(base_dir, "TeraChat-V0.2.1-TechSpec.md")
    html_template_path = os.path.join(base_dir, "TeraChat - V0.2.1 Alpha.html")
    output_path = os.path.join(base_dir, "TeraChat-V0.2.1-TechSpec.html")

    # Read Markdown
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    # Parse
    html_content, toc = parse_markdown(md_text)

    # Get CSS from template
    css = extract_style(html_template_path)

    # Build TOC HTML
    toc_html = '<div class="nav-header">Table of Contents</div>'
    for item in toc:
        if item['level'] <= 3: # Only showing H1-H3 in sidebar
            indent_class = "padding-left: 0.8rem;" if item['level'] > 1 else ""
            toc_html += f'<a href="#{item["anchor"]}" class="nav-link" style="{indent_class}">{item["text"]}</a>\n'

    # Construct Final HTML
    final_html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TeraChat Enterprise OS - Tech Spec</title>
    <style>
    {css}
    </style>
</head>
<body>

<nav class="sidebar">
    <a href="#" class="brand">TeraChat <span>Tech Spec</span></a>
    {toc_html}
</nav>

<div class="main">
    {html_content}
    
    <div style="margin-top: 4rem; padding-top: 2rem; border-top: 1px solid var(--border); color: var(--text-secondary); font-size: 0.9rem; text-align: center;">
        <p>TeraChat Enterprise OS &copy; 2026</p>
    </div>
</div>

</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"Successfully converted {md_path} to {output_path}")

if __name__ == "__main__":
    main()
