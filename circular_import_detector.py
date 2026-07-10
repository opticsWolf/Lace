#!/usr/bin/env python3
"""
Advanced circular import detector for Lace project.
"""

import os
import sys
from collections import defaultdict, deque

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def get_module_name_from_path(filepath):
    """Convert file path to module name."""
    rel_path = os.path.relpath(filepath, project_root)
    module_name = rel_path.replace(os.sep, '.').replace('.py', '')
    # Remove the 'lace.' prefix if present
    if module_name.startswith('lace.'):
        module_name = module_name[5:]  # Remove 'lace.'
    return module_name

def analyze_imports_in_file(filepath):
    """Analyze imports from a Python file."""
    imports = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
                
            # Handle relative imports (from .module import ...)
            if line.startswith('from .'):
                parts = line.split()
                if len(parts) >= 3 and parts[1] == 'import':
                    imported_module = parts[0][2:]  # Remove leading "."
                    imports.append(imported_module)
                    
            # Handle absolute imports (from lace.module import ...)
            elif line.startswith('from lace.'):
                parts = line.split()
                if len(parts) >= 3 and parts[2] == 'import':
                    imported_module = parts[1]
                    imports.append(imported_module)
                    
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        
    return imports

def detect_circular_imports():
    """Detect circular imports in the Lace project."""
    
    # Build mapping of file paths to module names
    file_to_module = {}
    module_to_file = {}
    
    # Walk through all Python files
    for root, dirs, files in os.walk(os.path.join(project_root, 'lace')):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                filepath = os.path.join(root, file)
                module_name = get_module_name_from_path(filepath)
                
                file_to_module[filepath] = module_name
                module_to_file[module_name] = filepath
    
    # Build import relationships graph
    import_graph = defaultdict(list)
    
    for filepath in file_to_module:
        module_name = file_to_module[filepath]
        
        imports = analyze_imports_in_file(filepath)
        
        # Process each import to build the dependency graph
        for imp in imports:
            if '.' in imp:  # It's a full path, extract just the module name
                import_module = imp.split('.')[-1]
            else:
                import_module = imp
                
            # Resolve relative imports properly
            if import_module in module_to_file:
                import_graph[module_name].append(import_module)
    
    print("Import Graph:")
    for module, deps in sorted(import_graph.items()):
        if deps:  # Only show modules that have dependencies
            print(f"  {module}:")
            for dep in deps:
                print(f"    -> {dep}")
    
    # Detect circular imports using DFS
    visited = set()
    rec_stack = set()  
    cycles = []
    
    def dfs(node, path):
        """Depth-first search to find cycles."""
        if node in rec_stack:
            cycle_start_index = path.index(node)
            cycle = path[cycle_start_index:] + [node]
            cycles.append(cycle)
            return
            
        if node in visited:
            return
            
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in import_graph[node]:
            # Make sure we're looking at the right module name
            if neighbor in file_to_module.values():
                dfs(neighbor, path)
        
        path.pop()
        rec_stack.remove(node)
    
    print("\nChecking for circular imports...")
    
    # Check each node
    for module_name in import_graph:
        if module_name not in visited:
            dfs(module_name, [])
    
    return cycles

def main():
    print("Advanced Circular Import Detection")
    print("=" * 40)
    
    cycles = detect_circular_imports()
    
    if cycles:
        print("\nCircular Imports Found:")
        for cycle in cycles:
            print(" -> ".join(cycle))
    else:
        print("\nNo circular imports detected!")

if __name__ == '__main__':
    main()