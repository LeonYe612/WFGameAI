import os
import sys

def mark_remaining_isolated_files():
    """Mark the remaining isolated files that haven't been marked yet."""
    # Read isolated files list
    print("Starting to mark remaining isolated files...")
    try:
        with open('isolated_files_report.txt', 'r') as f:
            content = f.read()
        print(f"Successfully read isolated_files_report.txt, size: {len(content)} bytes")
    except FileNotFoundError:
        print("Error: isolated_files_report.txt not found. Run the find_isolated_files.py script first.")
        return
    except Exception as e:
        print(f"Error reading isolated_files_report.txt: {e}")
        return    # Extract Python and HTML file sections
    py_section_start = content.find("--- ISOLATED PYTHON FILES ---")
    py_section_end = content.find("\nFound ", py_section_start)
    html_section_start = content.find("--- ISOLATED HTML FILES ---")

    print(f"Python section start: {py_section_start}, end: {py_section_end}")
    print(f"HTML section start: {html_section_start}")

    # Extract file lists
    if py_section_start != -1 and py_section_end != -1:
        py_files_text = content[py_section_start:py_section_end]
        py_files = [line.strip() for line in py_files_text.split("\n")[1:] if line.strip()]
    else:
        py_files = []

    if html_section_start != -1:
        html_files_text = content[html_section_start:]
        html_section_end = html_files_text.find("\nFound ")
        if html_section_end != -1:
            html_files_text = html_files_text[:html_section_end]
        html_files = [line.strip() for line in html_files_text.split("\n")[1:] if line.strip()]
    else:
        html_files = []

    print(f"Found {len(py_files)} Python files and {len(html_files)} HTML files in the report")

    # Read already marked files
    try:
        with open('marked_isolated_files.txt', 'r') as f:
            marked_content = f.read()
    except FileNotFoundError:
        marked_content = ""

    # Extract already marked files
    marked_py_files = []
    marked_html_files = []

    if "--- MARKED PYTHON FILES ---" in marked_content:
        py_marked_section = marked_content.split("--- MARKED PYTHON FILES ---")[1].split("Marked ")[0]
        marked_py_files = [line.split(" -> ")[0].strip() for line in py_marked_section.split("\n") if " -> " in line]

    if "--- MARKED HTML FILES ---" in marked_content:
        html_marked_section = marked_content.split("--- MARKED HTML FILES ---")[1].split("Marked ")[0]
        marked_html_files = [line.split(" -> ")[0].strip() for line in html_marked_section.split("\n") if " -> " in line]

    # Filter out already marked files
    remaining_py_files = [f for f in py_files if f not in marked_py_files]
    remaining_html_files = [f for f in html_files if f not in marked_html_files]

    # Calculate number of files to mark
    max_py_files_to_mark = 100  # Adjust these numbers as needed
    max_html_files_to_mark = 100

    py_files_to_mark = remaining_py_files[:max_py_files_to_mark]
    html_files_to_mark = remaining_html_files[:max_html_files_to_mark]

    # Mark files
    marked_py = []
    marked_html = []

    # Mark Python files
    for rel_path in py_files_to_mark:
        file_path = os.path.join(os.getcwd(), rel_path)
        if os.path.exists(file_path):
            # Get new path with _del suffix
            directory, filename = os.path.split(file_path)
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}_del{ext}"
            new_path = os.path.join(directory, new_filename)

            try:
                # Rename the file
                os.rename(file_path, new_path)
                marked_py.append((rel_path, os.path.join(os.path.dirname(rel_path), new_filename)))
                print(f"Marked as isolated: {rel_path} -> {new_filename}")
            except Exception as e:
                print(f"Error marking {rel_path}: {e}")

    # Mark HTML files
    for rel_path in html_files_to_mark:
        file_path = os.path.join(os.getcwd(), rel_path)
        if os.path.exists(file_path):
            # Get new path with _del suffix
            directory, filename = os.path.split(file_path)
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}_del{ext}"
            new_path = os.path.join(directory, new_filename)

            try:
                # Rename the file
                os.rename(file_path, new_path)
                marked_html.append((rel_path, os.path.join(os.path.dirname(rel_path), new_filename)))
                print(f"Marked as isolated: {rel_path} -> {new_filename}")
            except Exception as e:
                print(f"Error marking {rel_path}: {e}")

    # Update the marked files list
    with open('marked_isolated_files.txt', 'a') as f:
        # Add new Python files
        if marked_py:
            f.write("\n--- ADDITIONAL MARKED PYTHON FILES ---\n")
            for old_path, new_path in marked_py:
                f.write(f"{old_path} -> {new_path}\n")
            f.write(f"\nMarked {len(marked_py)} additional Python files\n")

        # Add new HTML files
        if marked_html:
            f.write("\n--- ADDITIONAL MARKED HTML FILES ---\n")
            for old_path, new_path in marked_html:
                f.write(f"{old_path} -> {new_path}\n")
            f.write(f"\nMarked {len(marked_html)} additional HTML files\n")

    print(f"Marked {len(marked_py)} additional Python files and {len(marked_html)} additional HTML files")
    print("Updated marked_isolated_files.txt")

    # Provide summary statistics
    total_py_files = len(py_files)
    total_html_files = len(html_files)
    marked_py_count = len(marked_py_files) + len(marked_py)
    marked_html_count = len(marked_html_files) + len(marked_html)

    print(f"\nSUMMARY:")
    print(f"Total isolated Python files: {total_py_files}")
    print(f"Total isolated HTML files: {total_html_files}")
    print(f"Python files marked: {marked_py_count}/{total_py_files}")
    print(f"HTML files marked: {marked_html_count}/{total_html_files}")

if __name__ == "__main__":
    mark_remaining_isolated_files()
