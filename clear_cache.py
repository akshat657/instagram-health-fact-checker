import streamlit as st
import shutil
from pathlib import Path

# Clear Streamlit cache
cache_dir = Path.home() / ".streamlit" / "cache"
if cache_dir.exists():
    shutil.rmtree(cache_dir)
    print("✅ Streamlit cache cleared!")

# Also clear .pyc files
import os
for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".pyc"):
            os.remove(os.path.join(root, file))
            
print("✅ All caches cleared!")