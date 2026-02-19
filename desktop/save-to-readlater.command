#!/bin/bash
# macOS: Double-click this file, or drag files onto it to save them to ReadLater.
# To use as a drop target: right-click > Get Info > Open with > change to Terminal.app

for arg in "$@"; do
    readlater add "$arg"
done

if [ $# -eq 0 ]; then
    echo "========================================="
    echo "  ReadLater - Drop files here to save"
    echo "========================================="
    echo ""
    read -p "Paste a URL or file path: " input
    readlater add "$input"
fi

echo ""
echo "Done! Press any key to close."
read -n 1
