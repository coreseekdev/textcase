"""
Document type definitions and utilities.

This module contains the DocumentCategory and DocumentType enums that define
the supported document types and their categories in the system.
"""
from enum import Enum
from typing import Dict, Optional, Type, TypeVar, Union

from tree_sitter import Language as TSLanguage


class DocumentCategory(str, Enum):
    """Document category types for logical grouping of document types."""
    # Programming languages
    PYTHON = "python"
    C = "c"
    CPP = "cpp"
    GO = "go"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    ZIG = "zig"
    
    # Styling
    CSS = "css"
    
    # Markup
    MARKDOWN = "markdown"
    
    # Build systems
    CMAKE = "cmake"
    
    # Data formats
    YAML = "yaml"
    JSON = "json"
    TOML = "toml"
    
    # Other
    SHELL = "shell"
    TEXT = "text"
    BINARY = "binary"
    UNKNOWN = "unknown"


class DocumentType(str, Enum):
    """Document types for specific file formats and languages.
    
    Each document type has a corresponding language name that can be used with tree-sitter.
    """
    # Python
    PYTHON = "python"
    PYI = "pyi"
    
    # C/C++
    C = "c"
    H = "h"
    CPP = "cpp"
    CXX = "cxx"
    CC = "cc"
    HPP = "hpp"
    HH = "hh"
    
    # Go
    GO = "go"
    
    # Java
    JAVA = "java"
    
    # JavaScript/TypeScript
    JAVASCRIPT = "js"
    JSX = "jsx"
    MJS = "mjs"
    TYPESCRIPT = "ts"
    TSX = "tsx"
    
    # Rust
    RUST = "rs"
    
    # Zig
    ZIG = "zig"
    
    # CSS/Styles
    CSS = "css"
    SCSS = "scss"
    SASS = "sass"
    LESS = "less"
    
    # Markup
    MARKDOWN = "md"
    MDX = "mdx"
    
    # Build systems
    CMAKE = "cmake"
    CMAKELISTS = "cmakelists"
    
    # Data formats
    YAML = "yaml"
    YML = "yml"
    JSON = "json"
    TOML = "toml"
    LOCK = "lock"
    
    # Other text
    TEXT = "txt"
    BINARY = "bin"
    UNKNOWN = "unknown"
    
    @property
    def language_name(self) -> str:
        """Get the tree-sitter language name for this document type.
        
        Returns:
            The tree-sitter language name
        """
        # Default mapping of document types to language names
        language_map = {
            # Python
            self.PYTHON: "python",
            self.PYI: "python",
            
            # C/C++
            self.C: "c",
            self.H: "c",
            self.CPP: "cpp",
            self.CXX: "cpp",
            self.CC: "cpp",
            self.HPP: "cpp",
            self.HH: "cpp",
            
            # Go
            self.GO: "go",
            
            # Java
            self.JAVA: "java",
            
            # JavaScript/TypeScript
            self.JAVASCRIPT: "javascript",
            self.JSX: "javascript",
            self.MJS: "javascript",
            self.TYPESCRIPT: "typescript",
            self.TSX: "typescript",
            
            # Rust
            self.RUST: "rust",
            
            # Zig
            self.ZIG: "zig",
            
            # CSS/Styles
            self.CSS: "css",
            self.SCSS: "scss",
            self.SASS: "sass",
            self.LESS: "less",
            
            # Markup
            self.MARKDOWN: "markdown",
            self.MDX: "markdown",
            
            # Build systems
            self.CMAKE: "cmake",
            self.CMAKELISTS: "cmake",
            
            # Data formats
            self.YAML: "yaml",
            self.YML: "yaml",
            self.JSON: "json",
            self.TOML: "toml",
            
            # Other
            self.LOCK: "text",
            self.TEXT: "text",
            self.BINARY: "text",
            self.UNKNOWN: "text",
        }
        
        return language_map.get(self, "text")

    @classmethod
    def from_extension(cls, extension: str) -> 'DocumentType':
        """Determine document type from file extension.
        
        Args:
            extension: File extension (e.g., "py", "md")
            
        Returns:
            Corresponding document type
        """
        if not extension:
            return cls.UNKNOWN
            
        extension = extension.lower().lstrip('.')
        
        # Special case for CMakeLists.txt
        if extension == 'txt' and 'cmakelists' in extension.lower():
            return cls.CMAKELISTS
            
        extension_map = {
            # Python
            'py': cls.PYTHON,
            'pyi': cls.PYI,
            
            # C/C++
            'c': cls.C,
            'h': cls.H,
            'cpp': cls.CPP,
            'cxx': cls.CXX,
            'cc': cls.CC,
            'hpp': cls.HPP,
            'hh': cls.HH,
            
            # Go
            'go': cls.GO,
            
            # Java
            'java': cls.JAVA,
            
            # JavaScript/TypeScript
            'js': cls.JAVASCRIPT,
            'jsx': cls.JSX,
            'mjs': cls.MJS,
            'ts': cls.TYPESCRIPT,
            'tsx': cls.TSX,
            
            # Rust
            'rs': cls.RUST,
            
            # Zig
            'zig': cls.ZIG,
            
            # CSS/Styles
            'css': cls.CSS,
            'scss': cls.SCSS,
            'sass': cls.SASS,
            'less': cls.LESS,
            
            # Markup
            'md': cls.MARKDOWN,
            'markdown': cls.MARKDOWN,
            'mdx': cls.MDX,
            
            # Build systems
            'cmake': cls.CMAKE,
            'cmakelists.txt': cls.CMAKELISTS,
            'cmakelists': cls.CMAKELISTS,
            
            # Data formats
            'yaml': cls.YAML,
            'yml': cls.YML,
            'json': cls.JSON,
            'toml': cls.TOML,
            'cargo.lock': cls.LOCK,
            'package-lock.json': cls.LOCK,
            'yarn.lock': cls.LOCK,
            'pnpm-lock.yaml': cls.LOCK,
            
            # Other text
            'txt': cls.TEXT,
        }
        return extension_map.get(extension, cls.UNKNOWN)
    
    @property
    def category(self) -> DocumentCategory:
        """Get the category of this document type."""
        category_map = {
            # Python
            self.PYTHON: DocumentCategory.PYTHON,
            self.PYI: DocumentCategory.PYTHON,
            
            # C/C++
            self.C: DocumentCategory.C,
            self.H: DocumentCategory.C,
            self.CPP: DocumentCategory.CPP,
            self.CC: DocumentCategory.CPP,
            self.CXX: DocumentCategory.CPP,
            self.HPP: DocumentCategory.CPP,
            self.HH: DocumentCategory.CPP,
            
            # Go
            self.GO: DocumentCategory.GO,
            
            # Java
            self.JAVA: DocumentCategory.JAVA,
            
            # JavaScript/TypeScript
            self.JAVASCRIPT: DocumentCategory.JAVASCRIPT,
            self.JSX: DocumentCategory.JAVASCRIPT,
            self.MJS: DocumentCategory.JAVASCRIPT,
            self.TYPESCRIPT: DocumentCategory.TYPESCRIPT,
            self.TSX: DocumentCategory.TYPESCRIPT,
            
            # Rust
            self.RUST: DocumentCategory.RUST,
            
            # Zig
            self.ZIG: DocumentCategory.ZIG,
            
            # CSS/Styles
            self.CSS: DocumentCategory.CSS,
            self.SCSS: DocumentCategory.CSS,
            self.SASS: DocumentCategory.CSS,
            self.LESS: DocumentCategory.CSS,
            
            # Markup
            self.MARKDOWN: DocumentCategory.MARKDOWN,
            self.MDX: DocumentCategory.MARKDOWN,
            
            # Build systems
            self.CMAKE: DocumentCategory.CMAKE,
            self.CMAKELISTS: DocumentCategory.CMAKE,
            
            # Data formats
            self.YAML: DocumentCategory.YAML,
            self.YML: DocumentCategory.YAML,
            self.JSON: DocumentCategory.JSON,
            self.TOML: DocumentCategory.TOML,
            self.LOCK: DocumentCategory.TEXT,  # Lock files as text
            
            # Other
            self.TEXT: DocumentCategory.TEXT,
            self.BINARY: DocumentCategory.BINARY,
            self.UNKNOWN: DocumentCategory.UNKNOWN,
        }
        return category_map.get(self, DocumentCategory.UNKNOWN)
    
    def get_language(self):
        """Get the tree-sitter language for this document type.
        
        Returns:
            The tree-sitter language object
            
        Raises:
            ValueError: If the language cannot be loaded
        """

        language_name = self.language_name
        
        try:
            # If that fails, try to get it from the language pack
            from tree_sitter_language_pack import get_language
            language = get_language(language_name)
            if language:
                return language
                
            raise ValueError(f"Language '{language_name}' not found in tree-sitter or language pack")
            
        except Exception as e:
            raise ValueError(f"Failed to load language '{language_name}': {str(e)}")
            
    def get_parser(self):
        """Get a tree-sitter parser configured for this document type.
        
        Returns:
            A configured tree-sitter Parser instance
            
        Raises:
            ValueError: If the parser cannot be created
        """
        from tree_sitter_language_pack import get_parser
        
        try:
            parser = get_parser(self.language_name)
            return parser
        except Exception as e:
            raise ValueError(f"Failed to create parser for {self}: {str(e)}")
