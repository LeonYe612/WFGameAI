#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update HTML links in template files to point to the correct template files with _template suffix.
"""

import os
import re

# Directory containing the HTML templates
templates_dir = os.path.join(os.path.dirname(__file__), 'staticfiles', 'pages')

# List of templates that need the _template suffix
template_files = set([
    'automation', 'dashboard', 'data', 'index', 'reports',
    'report_detail', 'settings', 'tasks'
])

# Print the list of files in the templates directory
print("Files in templates directory:")
for filename in sorted(os.listdir(templates_dir)):
    if filename.endswith('.html'):
        print(f"  - {filename}")

# Regular expression to find links
link_pattern = re.compile(r'href="/pages/([a-zA-Z_]+)(\.html)"')

# Process all HTML files in the templates directory
def update_links():
    updated_files = 0

    for filename in os.listdir(templates_dir):
        if not filename.endswith('.html'):
            continue

        file_path = os.path.join(templates_dir, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all links in the file
            links = link_pattern.findall(content)
            if links:
                print(f"Links found in {filename}:")
                for page_name, extension in links:
                    print(f"  - {page_name}{extension}")

                    # Check if this link should be updated
                    if page_name in template_files:
                        print(f"    -> Should be updated to {page_name}_template{extension}")

            # Function to replace links with template links where needed
            def replace_link(match):
                page_name = match.group(1)
                extension = match.group(2)

                if page_name in template_files:
                    return f'href="/pages/{page_name}_template{extension}"'
                return match.group(0)

            # Replace links in the content
            new_content = link_pattern.sub(replace_link, content)

            # If changes were made, write the file
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated links in {filename}")
                updated_files += 1
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    print(f"Updated {updated_files} files.")

if __name__ == "__main__":
    update_links()

if __name__ == "__main__":
    update_links()
