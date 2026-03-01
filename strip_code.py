import re

def remove_code_blocks(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Define languages to remove (everything except mermaid, text, or empty)
    to_remove = ['bash', 'kotlin', 'smt2', 'json', 'typescript', 'protobuf', 'swift', 'rust', 'rego', 'cpp', 'sql', 'yaml']
    
    # We use a function to substitute matches
    def replacer(match):
        lang = match.group(1)
        if lang in to_remove:
            return '' # Remove the entire block
        return match.group(0) # Keep the block

    # Regex to match code blocks ```language ... ```
    new_content = re.sub(r'```([a-zA-Z0-9_\-]+)?\n.*?```\n', replacer, content, flags=re.DOTALL)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("Removed code blocks.")

remove_code_blocks('TechSpec.md')
