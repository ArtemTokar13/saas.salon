#!/bin/bash
# Quick Git Corruption Recovery Script
# Run this if you see "object file is empty" errors

echo "=== Git Corruption Recovery Script ==="
echo ""

# Check for corruption
echo "Checking for corruption..."
corrupted=$(find .git/objects -type f -size 0 2>/dev/null | wc -l)

if [ "$corrupted" -eq 0 ]; then
    echo "✓ No corrupted objects found!"
    git fsck --full
    exit 0
fi

echo "✗ Found $corrupted corrupted (empty) object files"
echo ""

# List corrupted files
echo "Corrupted files:"
find .git/objects -type f -size 0

echo ""
read -p "Remove corrupted files and recover from remote? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing corrupted files..."
    find .git/objects -type f -size 0 -delete
    
    echo "Fetching from remote..."
    git fetch origin --force
    
    echo ""
    echo "Verifying repository..."
    git fsck --full
    
    echo ""
    echo "Repository status:"
    git status
    
    echo ""
    echo "✓ Recovery complete!"
else
    echo "Recovery cancelled"
    exit 1
fi
