import os
import sys
import glob
import re
import ast
from collections import defaultdict
import os.path as osp

# Constants
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ISOLATED_SUFFIX = "_del"  # Suffix to add to isolated files

# Track imports and references
python_imports = defaultdict(set)  # file -> set of imported files
file_references = defaultdict(set)  # file -> set of files that import it
html_references = defaultdict(set)  # html -> set of files that reference it

# Functions to analyze Python files
def extract_imports(file_path):
    """Extract import statements from a Python file"""
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            file_content = f.read()

        # Try to parse with AST first
        try:
            tree = ast.parse(file_content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.add(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
        except SyntaxError:
            # Fallback to simple regex for problematic files
            import_pattern = re.compile(r'^\s*(?:from\s+(\S+)\s+import|\s*import\s+([^,\s]+))', re.MULTILINE)
            for match in import_pattern.finditer(file_content):
                module = match.group(1) or match.group(2)
                if module:
                    imports.add(module)

        # Also check for template references in Django/Flask views
        template_pattern = re.compile(r'[\'"]([^\'\"]+\.html)[\'"]')
        for match in template_pattern.finditer(file_content):
            template_name = match.group(1)
            html_references[template_name].add(file_path)

        return imports
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return set()

def check_html_references(html_file, python_files):
    """Check if HTML file is referenced in any Python file"""
    html_name = os.path.basename(html_file)
    if html_name in html_references:
        return True

    # Also check direct references in all Python files
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if html_name in content or html_file.replace(PROJECT_ROOT, '').replace('\\', '/') in content:
                    html_references[html_name].add(py_file)
                    return True
        except Exception:
            continue

    return False

def resolve_python_module(import_name, file_path):
    """Convert an import statement to a potential file path"""
    # This is a simplified resolver - a real one would be more complex
    parts = import_name.split('.')

    # Handle relative imports
    if import_name.startswith('.'):
        current_dir = os.path.dirname(file_path)
        for _ in range(len(import_name) - len(import_name.lstrip('.'))):
            current_dir = os.path.dirname(current_dir)
        base_path = current_dir
        parts = parts[parts.count(''):] # Remove empty strings from relative imports
    else:
        base_path = PROJECT_ROOT

    # Try different possible paths
    possible_paths = []

    # 1. Direct module file
    module_path = os.path.join(base_path, *parts) + '.py'
    possible_paths.append(module_path)

    # 2. Package with __init__.py
    package_path = os.path.join(base_path, *parts, '__init__.py')
    possible_paths.append(package_path)

    # Return paths that exist
    return [p for p in possible_paths if os.path.exists(p)]

def build_dependency_graph():
    """Build dependency graph of Python files"""
    python_files = glob.glob(os.path.join(PROJECT_ROOT, '**', '*.py'), recursive=True)
    html_files = glob.glob(os.path.join(PROJECT_ROOT, '**', '*.html'), recursive=True)

    print(f"Found {len(python_files)} Python files and {len(html_files)} HTML files")

    # Save the file lists for debugging
    with open('all_files_found.txt', 'w') as f:
        f.write("PYTHON FILES:\n")
        for py_file in python_files:
            f.write(f"{py_file}\n")

        f.write("\nHTML FILES:\n")
        for html_file in html_files:
            f.write(f"{html_file}\n")

    # Process Python files
    counter = 0
    total = len(python_files)
    for file_path in python_files:
        counter += 1
        if counter % 100 == 0:
            print(f"Processing Python file {counter}/{total}: {os.path.basename(file_path)}")
        imports = extract_imports(file_path)
        for import_name in imports:
            resolved_paths = resolve_python_module(import_name, file_path)
            for resolved_path in resolved_paths:
                python_imports[file_path].add(resolved_path)
                file_references[resolved_path].add(file_path)

    # Find isolated Python files
    isolated_py_files = []
    for file_path in python_files:
        rel_path = os.path.relpath(file_path, PROJECT_ROOT)

        # Skip __init__.py files and specific directories known to be important
        if os.path.basename(file_path) == '__init__.py':
            continue

        # Skip main Django files which are always necessary
        if 'settings.py' in file_path or 'urls.py' in file_path or 'wsgi.py' in file_path or 'asgi.py' in file_path:
            continue

        # If the file is not imported by any other file, it might be isolated
        if file_path not in file_references:
            # Check if it's a script that might be run directly
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # If it has __main__ check or appears to be a standalone script, it's not isolated
                if "__name__ == '__main__'" in content or "if __name__ == \"__main__\"" in content:
                    continue

            isolated_py_files.append(rel_path)

    # Find isolated HTML files
    print("Processing HTML files to find isolated ones...")
    isolated_html_files = []
    html_counter = 0
    html_total = len(html_files)
    for html_file in html_files:
        html_counter += 1
        if html_counter % 50 == 0:
            print(f"Processing HTML file {html_counter}/{html_total}: {os.path.basename(html_file)}")
        rel_path = os.path.relpath(html_file, PROJECT_ROOT)

        # Skip certain template patterns that are likely important
        if 'base.html' in html_file or 'layout.html' in html_file:
            continue

        # If the HTML is not referenced anywhere
        if not check_html_references(html_file, python_files):
            isolated_html_files.append(rel_path)

    return isolated_py_files, isolated_html_files

    # Process Python files
    for file_path in python_files:
        imports = extract_imports(file_path)
        for import_name in imports:
            resolved_paths = resolve_python_module(import_name, file_path)
            for resolved_path in resolved_paths:
                python_imports[file_path].add(resolved_path)
                file_references[resolved_path].add(file_path)

    # Find isolated Python files
    isolated_py_files = []
    for file_path in python_files:
        rel_path = os.path.relpath(file_path, PROJECT_ROOT)

        # Skip __init__.py files and specific directories known to be important
        if os.path.basename(file_path) == '__init__.py':
            continue

        # Skip main Django files which are always necessary
        if 'settings.py' in file_path or 'urls.py' in file_path or 'wsgi.py' in file_path or 'asgi.py' in file_path:
            continue

        # If the file is not imported by any other file, it might be isolated
        if file_path not in file_references:
            # Check if it's a script that might be run directly
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # If it has __main__ check or appears to be a standalone script, it's not isolated
                if "__name__ == '__main__'" in content or "if __name__ == \"__main__\"" in content:
                    continue

            isolated_py_files.append(rel_path)

    # Find isolated HTML files
    isolated_html_files = []
    for html_file in html_files:
        rel_path = os.path.relpath(html_file, PROJECT_ROOT)

        # Skip certain template patterns that are likely important
        if 'base.html' in html_file or 'layout.html' in html_file:
            continue

        # If the HTML is not referenced anywhere
        if not check_html_references(html_file, python_files):
            isolated_html_files.append(rel_path)

    return isolated_py_files, isolated_html_files

def mark_isolated_files(isolated_files):
    """Mark isolated files by renaming them with _del suffix"""
    marked_files = []

    for rel_path in isolated_files:
        file_path = os.path.join(PROJECT_ROOT, rel_path)
        if os.path.exists(file_path):
            # Get new path with _del suffix
            directory, filename = os.path.split(file_path)
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}{ISOLATED_SUFFIX}{ext}"
            new_path = os.path.join(directory, new_filename)

            try:
                # Rename the file
                os.rename(file_path, new_path)
                marked_files.append((rel_path, os.path.relpath(new_path, PROJECT_ROOT)))
                print(f"Marked as isolated: {rel_path} -> {os.path.basename(new_path)}")
            except Exception as e:
                print(f"Error marking {rel_path}: {e}")

    return marked_files

def main():
    isolated_py_files, isolated_html_files = build_dependency_graph()

    # Write results to file instead of printing and asking for input
    with open('isolated_files_report.txt', 'w') as f:
        f.write("--- ISOLATED PYTHON FILES ---\n")
        for file_path in isolated_py_files:
            f.write(f"{file_path}\n")

        f.write(f"\nFound {len(isolated_py_files)} isolated Python files\n")

        f.write("\n--- ISOLATED HTML FILES ---\n")
        for file_path in isolated_html_files:
            f.write(f"{file_path}\n")

        f.write(f"\nFound {len(isolated_html_files)} isolated HTML files\n")

    # Auto-mark a subset (first 20 of each) for testing
    mark_subset = 20  # Only mark the first N files of each type

    print(f"\nMarking isolated files (first {mark_subset} of each type)...")
    marked_py = mark_isolated_files(isolated_py_files[:mark_subset])
    marked_html = mark_isolated_files(isolated_html_files[:mark_subset])

    # Also save the marked files list
    with open('marked_isolated_files.txt', 'w') as f:
        f.write("--- MARKED PYTHON FILES ---\n")
        for old_path, new_path in marked_py:
            f.write(f"{old_path} -> {new_path}\n")

        f.write(f"\nMarked {len(marked_py)} Python files\n")

        f.write("\n--- MARKED HTML FILES ---\n")
        for old_path, new_path in marked_html:
            f.write(f"{old_path} -> {new_path}\n")

        f.write(f"\nMarked {len(marked_html)} HTML files\n")

    print(f"Marked {len(marked_py)} Python files and {len(marked_html)} HTML files")
    print("Results saved to isolated_files_report.txt and marked_isolated_files.txt")

if __name__ == "__main__":
    main()
