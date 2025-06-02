#!/usr/bin/env python3
"""Test script to verify all imports work correctly."""

import sys
import traceback

def test_import(module_name, description):
    """Test importing a module and report results."""
    try:
        exec(f"import {module_name}")
        print(f"✓ {description}")
        return True
    except Exception as e:
        print(f"✗ {description}: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all import tests."""
    print("Testing modular Quix Portal MCP server imports...\n")
    
    tests = [
        ("tools.base", "Base utilities module"),
        ("tools.applications", "Applications tools module"),
        ("tools.deployments", "Deployments tools module"),
        ("tools.library", "Library tools module"),
        ("tools.topics", "Topics tools module"),
        ("tools", "Tools package"),
    ]
    
    all_passed = True
    for module, description in tests:
        if not test_import(module, description):
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("✓ All import tests PASSED!")
        print("The modular server structure is working correctly.")
    else:
        print("✗ Some import tests FAILED!")
        print("Check the error messages above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()