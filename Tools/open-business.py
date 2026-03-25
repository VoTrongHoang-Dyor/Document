import subprocess
import os

files = [
    "/Users/hoang_dyor_i/Code_Projects/Antigravity/DocumentTeraChat/Html/Pitch_Deck.html",
    "/Users/hoang_dyor_i/Code_Projects/Antigravity/DocumentTeraChat/Html/Pricing_Packages.html",
    "/Users/hoang_dyor_i/Code_Projects/Antigravity/DocumentTeraChat/Html/Executive_Summary.html"
]

for file_path in files:
    if os.path.exists(file_path):
        subprocess.run(["open", file_path])
        print(f"Opened: {file_path}")
    else:
        print(f"File not found: {file_path}")
