import os
import shutil
import sys
from datetime import datetime

def backup_files(file_list, backup_dir):
    """Backup files before deletion"""
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    for file_path in file_list:
        if os.path.exists(file_path):
            # Preserve directory structure in backup
            rel_path = os.path.relpath(file_path, os.getcwd())
            backup_path = os.path.join(backup_dir, rel_path)
            backup_dir_path = os.path.dirname(backup_path)

            if not os.path.exists(backup_dir_path):
                os.makedirs(backup_dir_path)

            # Copy file to backup
            shutil.copy2(file_path, backup_path)
            print(f"Backed up: {rel_path}")

def remove_marked_files(dry_run=True):
    """Remove files marked with _del suffix"""
    # Create timestamp for backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f"isolated_files_backup_{timestamp}"

    print("Searching for files with '_del.' suffix...")

    # Collect marked files
    marked_files = []
    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            if "_del." in file:
                file_path = os.path.join(root, file)
                marked_files.append(file_path)
                if len(marked_files) <= 5:  # Just show the first few for debugging
                    print(f"Found: {os.path.relpath(file_path, os.getcwd())}")

    if not marked_files:
        print("No files found with '_del.' suffix. Make sure files have been marked properly.")
        return

    print(f"Found {len(marked_files)} files marked for deletion")

    # In dry run mode, just list files
    if dry_run:
        print("\nDRY RUN - No files will be deleted\n")

        # Group by directory for cleaner output
        files_by_dir = {}
        for file_path in marked_files:
            dir_path = os.path.dirname(file_path)
            if dir_path not in files_by_dir:
                files_by_dir[dir_path] = []
            files_by_dir[dir_path].append(os.path.basename(file_path))

        # Display files by directory
        for dir_path, files in sorted(files_by_dir.items()):
            rel_dir = os.path.relpath(dir_path, os.getcwd())
            print(f"\nDirectory: {rel_dir}")
            for file in sorted(files):
                print(f"  {file}")

        print(f"\nTOTAL: {len(marked_files)} files would be deleted")
        print("Run with --execute to perform actual deletion")
    else:
        # Backup before deleting
        print("\nBacking up files before deletion...")
        backup_files(marked_files, backup_dir)

        # Delete files
        print("\nDeleting marked files...")
        for file_path in marked_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted: {os.path.relpath(file_path, os.getcwd())}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

        print(f"\nDeletion complete. {len(marked_files)} files were deleted.")
        print(f"Backup saved to: {backup_dir}")

if __name__ == "__main__":
    # Check for execute flag
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        remove_marked_files(dry_run=False)
    else:
        remove_marked_files(dry_run=True)
