import re

file_path = '/Users/hoang_dyor_i/Code_Projects/DocumentTeraChat/TeraChat - Alpha 2e58a8358a9c80fcbf8bd51fd95038b7.html'

with open(file_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

# Remove style and script tags content
clean_content = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL)

# Extract text from tags, adding newlines for block elements
# Helper to replace block tags with newlines
def replace_block_tags(match):
    tag = match.group(0)
    if re.match(r'<(div|p|h[1-6]|li|tr|br)', tag):
        return '\n' + tag
    return tag

# Add newlines before block tags for better separation
clean_content = re.sub(r'<[^>]+>', replace_block_tags, clean_content)

# Remove all tags
text_content = re.sub(r'<[^>]+>', ' ', clean_content)

# Clean up whitespace
lines = [line.strip() for line in text_content.split('\n') if line.strip()]
final_text = '\n'.join(lines)

print(final_text)
