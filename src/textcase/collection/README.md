# Resource Collection Implementation

This module provides a concrete implementation of the resource collection protocols defined in `textcase.proto.resource_collection_protocol`. The implementation follows the design patterns from the original `textcase.orig.core` modules and uses VFS for all file operations.

## Architecture Overview

The collection system consists of several key components:

### Core Components

1. **ResourceCollectionManagerImpl** - The main manager that handles collection hierarchies
2. **ResourceCollectionImpl** - Individual collection implementation
3. **ResourceItemImpl** - Individual item implementation within collections
4. **CollectionConfig** - YAML-based configuration for collections
5. **CollectionFactory** - Factory for simplified collection creation and management

### File Structure

The implementation uses the following file structure:

```
git_repo_root/
├── .textcase.yml                 # Collection manager configuration
└── collections/                  # Default collections directory
    ├── requirements/             # Example collection directory
    │   ├── .textcase.yml        # Collection metadata
    │   ├── REQ-001.md           # Item files
    │   ├── REQ-002.md
    │   ├── functional.txt       # Tag file (contains item names)
    │   └── business.txt
    └── design/
        ├── .textcase.yml
        ├── DES-001.md
        └── architecture.txt
```

## Key Design Decisions

### 1. VFS-Only File Operations

All file operations go through the VFS client (`vfs_client.py`), ensuring consistency with the existing codebase and enabling features like version control integration.

### 2. YAML Configuration

Following the pattern from `module_config.py`, collections store their metadata in `.textcase.yml` files:

```yaml
name: requirements
prefix: REQ
num: 3
sep: "-"
suffix: ".md"
tags:
  functional: "Functional requirements"
  business: "Business requirements"
settings:
  auto_numbering: true
```

### 3. Tag Files

Similar to `FileBasedModuleTags`, each tag is stored as a text file where each line contains an item name:

```
# functional.txt
REQ001
REQ003
REQ005
```

### 4. Hierarchical Collections

The collection manager stores hierarchy information in the root `.textcase.yml`:

```yaml
collections:
  requirements:
    parent: null
    children: ["detailed-requirements"]
    path: "collections/requirements"
  detailed-requirements:
    parent: "requirements"
    children: []
    path: "collections/requirements/detailed"
root_collection: "requirements"
```

### 5. Item Naming Convention

Items follow the naming pattern from the original module system:
- **File name**: `{prefix}{sep}{number}{suffix}` (e.g., `REQ-001.md`)
- **Item name**: `{prefix}{number}` (e.g., `REQ001`)

## Usage Examples

### Basic Setup

```python
from textcase.client.vfs_client import VFSClient
from textcase.collection import CollectionFactory

# Initialize VFS client and factory
vfs = VFSClient(server_url="tcp://localhost:4242")
factory = CollectionFactory(vfs)

# Get collection manager for a repository
manager = factory.get_manager("/path/to/git/repo")
```

### Creating Collections

```python
# Create a root collection
requirements = manager.create_collection("requirements")

# Configure the collection
config = requirements.config
config.prefix = "REQ"
config.num = 3
config.sep = "-"
config.suffix = ".md"
requirements._save_config()

# Add tags
requirements.add_tag("functional", "Functional requirements")
requirements.add_tag("business", "Business requirements")

# Create a sub-collection
detailed = manager.create_collection(
    "detailed-requirements", 
    parent="requirements"
)
```

### Working with Items

```python
# Add items to collection
req1 = requirements.add_item("REQ001")
req1.write_content("# User Authentication\n\nThe system shall...")
req1.add_tag("functional")

# Get next available item name
next_name = requirements.get_next_item_name()  # "REQ002"
req2 = requirements.add_item(next_name)

# Search and filter
functional_items = requirements.get_items_by_tag("functional")
all_items = list(requirements.iter_items())
```

### Project Setup

```python
# Set up default collections for a new project
manager = factory.setup_default_collections("/path/to/repo")

# This creates:
# - requirements (REQ prefix, functional/business/non-functional tags)
# - design (DES prefix, architecture/ui/api tags)
# - tests (TST prefix, unit/integration/e2e tags)
```

## VFS Interface Requirements

The current implementation assumes the following VFS operations are available:

### Currently Used
- `info(path)` - Check if file/directory exists
- `list(path)` - List directory contents
- `get_text(path, encoding)` - Read text file
- `put(path, content, create_if_missing)` - Write file

### Missing but Needed
- `delete(path)` - Delete files (for item/tag removal)
- `mkdir(path)` - Create directories (for collection setup)

## Suggested VFS Enhancements

To fully support the collection system, the VFS interface should be extended with:

```python
class VFSClient:
    def delete(self, path: Union[str, PurePosixPath]) -> bool:
        """Delete a file or directory."""
        
    def mkdir(self, path: Union[str, PurePosixPath], parents: bool = True) -> bool:
        """Create a directory."""
        
    def exists(self, path: Union[str, PurePosixPath]) -> bool:
        """Check if a path exists (convenience method)."""
        
    def is_file(self, path: Union[str, PurePosixPath]) -> bool:
        """Check if path is a file."""
        
    def is_dir(self, path: Union[str, PurePosixPath]) -> bool:
        """Check if path is a directory."""
```

## Error Handling

The implementation uses `VFSClientException` for all VFS-related errors, maintaining consistency with the existing error handling patterns.

## Thread Safety

The implementation is designed to be thread-safe when used with a thread-safe VFS client. Collections and items cache data locally but always read from/write to VFS for persistence.

## Performance Considerations

1. **Caching**: Collections and items are cached in memory to reduce VFS calls
2. **Lazy Loading**: Configuration and item data are loaded on-demand
3. **Batch Operations**: Tag updates are batched when possible
4. **Efficient Search**: Tag-based searches use dedicated tag files for fast lookup

## Migration from Original System

To migrate from the original `textcase.orig.core` system:

1. **Projects** → **ResourceCollectionManager**
2. **Modules** → **ResourceCollection**
3. **Module Items** → **ResourceItem**
4. **Module Config** → **CollectionConfig**
5. **Module Tags** → Collection tag system

The new system provides the same functionality with improved type safety, better separation of concerns, and more flexible hierarchy management.