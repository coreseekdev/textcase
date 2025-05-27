#
# Copyright 2025 coreseek.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Example usage of the module system."""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from pathlib import Path

from textcase.core import create_project, get_default_vfs

def main():
    # Create or load project
    project_path = Path("example_project").resolve()
    vfs = get_default_vfs()
    
    # Clean up from previous runs
    if vfs.exists(project_path):
        print(f"Removing existing project at {project_path}")
        vfs.rmtree(project_path)
    
    print(f"\nCreating new project at {project_path}")
    project = create_project(project_path)
    
    # Configure project settings
    project.config.settings.update({
        'digits': 3,
        'prefix': 'REQ',
        'sep': '',
        'default_tag': ['important']
    })


    
    # Configure project tags
    project.config.tags.update({
        'important': 'High priority items',
        'documentation': 'Documentation related items'
    })
    
    # Example of getting document items with different settings
    print("\nTesting document item key formatting:")
    
    # Test with default settings (no separator, 3 digits)
    project.config.settings.update({
        'digits': 3,
        'sep': '',
        'prefix': 'REQ'
    })
    item1 = project.get_document_item("1")
    print(f"\n1. Default settings (digits=3, sep=''):")
    print(f"   Input ID: '1' -> Key: {item1.key} (prefix: {item1.prefix}, id: {item1.id})")
    
    # Test with separator and different digits
    project.config.settings.update({
        'digits': 4,
        'sep': '-',
        'prefix': 'REQ'
    })
    item2 = project.get_document_item("42")
    print(f"\n2. With separator and 4 digits:")
    print(f"   Input ID: '42' -> Key: {item2.key} (prefix: {item2.prefix}, id: {item2.id})")
    
    # Test with non-numeric ID
    item3 = project.get_document_item("ABC")
    print(f"\n3. Non-numeric ID:")
    print(f"   Input ID: 'ABC' -> Key: {item3.key} (prefix: {item3.prefix}, id: {item3.id})")
    
    # Restore original settings
    project.config.settings.update({
        'digits': 3,
        'sep': '',
        'prefix': 'REQ'
    })
    
    # Save the initial configuration
    project.save()
    
    # Print project info
    print(f"\nProject path: {project.path}")
    print(f"Settings: {project.config.settings}")
    print(f"Tags: {project.config.tags}")
    
    # Create a submodule
    try:
        print("\nCreating 'requirements' submodule...")
        
        # Create the module directory first
        module_path = project.path / "unittests"
        vfs.makedirs(module_path, exist_ok=True)
        
        # Create the module instance
        from textcase.core.module import YamlModule
        from textcase.core.module_config import YamlModuleConfig
        
        # Create and configure the module
        submodule = YamlModule(module_path, vfs)
        
        # Configure the module with a prefix
        submodule.config.settings.update({
            'prefix': 'TST',
            'digits': 3,
            'sep': '',
            'default_tag': ['important']
        })
        
        # Save the module's config first
        submodule.save()
        
        # Add the module to the project with the project's prefix as parent
        project.add_module(parent_prefix=project.config.settings['prefix'], module=submodule)
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
        
        # Get the document item using the module's get_document_item method
        # The ID is just the numeric part, prefix comes from the module's settings
        doc_id = rel_path.stem.replace(project.config.settings['prefix'], '')  # Remove prefix if present
        doc_item = submodule.get_document_item(doc_id)
        print(f"\nDocument Item Info:")
        print(f"  - Key: {doc_item.key}")
        print(f"  - Display ID: {doc_item.display_id}")
        print(f"  - Prefix: {doc_item.prefix}")
        print(f"  - ID: {doc_item.id}")
        print(f"  - Separator: '{doc_item.sep}'")
        
        # Add multiple tags to the document
        tags_to_add = ["important", "documentation", "high-priority"]
        for tag in tags_to_add:
            print(f"Adding tag '{tag}' to {doc_item.key}...")
            try:
                submodule.tags.add_tag(doc_item, tag)
                print(f"  - Successfully added tag: {tag}")
            except ValueError as e:
                print(f"  - Could not add tag '{tag}': {e}")
        
        # Save changes
        print("\nSaving project...")
        project.save()
        
        # Print module info
        print("\nSubmodule order:")
        for item in submodule.order.get_ordered_items():
            print(f"  - {item}")
        
        # Get and print all available tags
        print("\nAll available tags:")
        for tag in project.tags.get_tags():
            print(f"  - {tag}")
            
        # Get and print tags specifically for our document
        print("\nTags for the document: %s" % doc_item.key)
        doc_tags = submodule.tags.get_item_tags(doc_item)
        if doc_tags:
            for tag in doc_tags:
                print(f"  - {tag}")
        else:
            print("  No tags found for this document")
        
        # Create a submodule under TST module
        print("\nCreating 'spectest' submodule under TST...")
        
        # Create the submodule directory
        submodule_path = project.path / "spectest"
        vfs.makedirs(submodule_path, exist_ok=True)
        
        # Create the submodule instance
        from textcase.core.module import YamlModule
        
        # Create and configure the submodule
        submodule_lst = YamlModule(submodule_path, vfs)
        
        # Configure the submodule with a prefix
        submodule_lst.config.settings.update({
            'prefix': 'LST',
            'digits': 3,
            'sep': '',
            'default_tag': ['test']
        })
        
        # Save the submodule's config first
        submodule_lst.save()
        
        # Add the submodule to the project with TST as parent
        project.add_module(parent_prefix=submodule.prefix, module=submodule_lst)
        print(f"Created submodule at: {submodule_lst.path}")
        
        # Save project again to include the new submodule
        project.save()
        print("\nUpdated project with new submodule.")
        
        # Create another submodule under TST module with path in unittests directory
        print("\nCreating 'hightest' submodule under TST in unittests/hightest...")
        
        # Create the submodule directory inside the TST module
        hst_module_path = submodule.path / "hightest"
        vfs.makedirs(hst_module_path, exist_ok=True)
        
        # Create the submodule instance
        submodule_hst = YamlModule(hst_module_path, vfs)
        
        # Configure the submodule with a prefix
        submodule_hst.config.settings.update({
            'prefix': 'HST',
            'digits': 3,
            'sep': '',
            'default_tag': ['high']
        })
        
        # Save the submodule's config first
        submodule_hst.save()
        
        # Add the submodule to the project with TST as parent
        project.add_module(parent_prefix=submodule.prefix, module=submodule_hst)
        print(f"Created submodule at: {submodule_hst.path}")
        
        # Save project again to include the new submodule
        project.save()
        print("\nUpdated project with HST submodule under TST.")
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        import traceback
        print(f"\nError: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
