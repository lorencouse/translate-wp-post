#!/bin/bash
cd "$(dirname "$0")"
python3 translate-post.py
read -p "Press Enter to exit..."
