"""Error result container for VFS service operations.

This module provides ErrorResult container to wrap exceptions as return values
instead of raising them, avoiding RPC framework exception reporting.
"""

from typing import Any, Optional, Union, TypeVar, Tuple
import traceback

# Generic type variable for result types
T = TypeVar('T')

# ErrorResult is now a tuple: (error_type, message, traceback_str)
ErrorResult = Tuple[str, str, str, Optional[str]]


def create_error_result(error_type: str, message: str, traceback_str: Optional[str] = None) -> ErrorResult:
    """Create an ErrorResult tuple.
    
    Args:
        error_type: Type name of the original exception
        message: Error message from the original exception
        traceback_str: String representation of the traceback
        
    Returns:
        ErrorResult tuple containing the exception information
    """
    return ('ErrorResult', error_type, message, traceback_str)


def error_result_from_exception(exc: Exception) -> ErrorResult:
    """Create ErrorResult from an exception.
    
    Args:
        exc: The exception to wrap
        
    Returns:
        ErrorResult tuple containing the exception information
    """
    return create_error_result(
        error_type=type(exc).__name__,
        message=str(exc),
        traceback_str=traceback.format_exc()
    )


def error_result_to_dict(error_result: ErrorResult) -> dict:
    """Convert ErrorResult tuple to dictionary for serialization.
    
    Args:
        error_result: ErrorResult tuple
        
    Returns:
        Dictionary representation of the error
    """
    _, error_type, message, traceback_str = error_result
    return {
        'error_type': error_type,
        'message': message,
        'traceback_str': traceback_str
    }


def error_result_from_dict(data: dict) -> ErrorResult:
    """Create ErrorResult from dictionary.
    
    Args:
        data: Dictionary containing error information
        
    Returns:
        ErrorResult tuple
    """
    return create_error_result(
        error_type=data['error_type'],
        message=data['message'],
        traceback_str=data.get('traceback_str')
    )


def is_error_result(value: Any) -> bool:
    """Check if a value is an ErrorResult tuple.
    
    Args:
        value: Value to check
        
    Returns:
        True if value is an ErrorResult tuple, False otherwise
    """
    if isinstance(value, tuple) and value[0] == 'ErrorResult':
        return True
    if isinstance(value, list) and value[0] == 'ErrorResult':
        return True

# Type alias for operations that can return either a result or an error
ResultOrError = Union[T, ErrorResult]