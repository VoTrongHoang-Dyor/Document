import subprocess
import os

files = [
    "/Users/hoang_dyor_i/Code_Projects/Antigravity/DocumentTeraChat/Html/TeraChat.html",
    "/Users/hoang_dyor_i/Code_Projects/Antigravity/DocumentTeraChat/Html/Web_Marketplace.html",
    "/Users/hoang_dyor_i/Code_Projects/Antigravity/DocumentTeraChat/Html/Introduction.html",
    "/Users/hoang_dyor_i/Code_Projects/Antigravity/DocumentTeraChat/Html/Function.html",
    "/Users/hoang_dyor_i/Code_Projects/Antigravity/DocumentTeraChat/Html/Feature_Spec.html",
    "/Users/hoang_dyor_i/Code_Projects/Antigravity/DocumentTeraChat/Html/Design.html",
    "/Users/hoang_dyor_i/Code_Projects/Antigravity/DocumentTeraChat/Html/Core_Spec.html"
]

for file_path in files:
    if os.path.exists(file_path):
        subprocess.run(["open", file_path])
        print(f"Opened: {file_path}")
    else:
        print(f"File not found: {file_path}")
