"""Example usage of the module system."""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from textcase.core import LocalVFS, ProjectModule

def main():
    # Initialize VFS
    vfs = LocalVFS()
    
    # Create or load project
    project_path = Path("example_project").resolve()
    
    # Clean up from previous runs
    if vfs.exists(project_path):
        print(f"Removing existing project at {project_path}")
        vfs.rmtree(project_path)
    
    print(f"\nCreating new project at {project_path}")
    project = ProjectModule.create(
        path=project_path,
        vfs=vfs,
        settings={
            'digits': 3,
            'prefix': 'REQ',
            'sep': '',
            'default_tag': ['important']
        },
        tags={
            'important': 'High priority items',
            'documentation': 'Documentation related items'
        }
    )
    
    # Print project info
    print(f"\nProject path: {project.path}")
    print(f"Settings: {project.config.settings}")
    print(f"Tags: {project.config.tags}")
    
    # Create a submodule
    try:
        print("\nCreating 'requirements' submodule...")
        submodule = project.create_submodule("requirements")
        print(f"Created submodule at: {submodule.path}")
        
        # Create a file in the submodule
        file_name = "REQ001.md"
        file_path = submodule.path / file_name
        file_content = "# Sample Requirement\n\nThis is a sample requirement."
        
        print(f"\nCreating file: {file_path}")
        with vfs.open(str(file_path), 'w') as f:
            f.write(file_content)
        
        # Add file to order
        rel_path = Path(file_name)
        print(f"Adding {rel_path} to module order...")
        submodule.order.add_item(rel_path)
        
        # Add a tag to the file
        print(f"Adding tag 'important' to {rel_path}...")
        submodule.tags.add_tag(rel_path, "important")
        
        # Save changes
        print("\nSaving project...")
        project.save()
        
        # Print module info
        print("\nSubmodule order:")
        for item in submodule.order.get_ordered_items():
            print(f"  - {item}")
        
        print("\nSubmodule tags:")
        for tag, items in submodule.tags.get_tags().items():
            print(f"  {tag}: {[str(i) for i in items]}")
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        import traceback
        print(f"\nError: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
