"""
Custom exceptions for PICO application.
"""
class PICOError(Exception):
    """Base exception for PICO application."""
    pass

class StorageError(PICOError):
    """Exception raised for storage-related errors."""
    pass

class TranscriptionError(PICOError):
    """Exception raised for transcription-related errors."""
    pass

class PrivacyError(PICOError):
    """Exception raised for privacy-related errors."""
    pass

class InputError(PICOError):
    """Exception raised for input-related errors."""
    pass

class ConfigurationError(PICOError):
    """Exception raised for configuration-related errors."""
    pass

class DatabaseError(PICOError):
    """Exception raised for database-related errors."""
    pass

class NetworkError(PICOError):
    """Exception raised for network-related errors."""
    pass

class ValidationError(PICOError):
    """Exception raised for validation-related errors."""
    pass