"""
Pipeline Module
---------------
Contains orchestration pipelines for artifact analysis and presentation generation.
"""

# Lazy imports to avoid dependency issues
# Users can import directly: from src.pipeline.orchestrator import ArtifactPipeline
# or from src.pipeline.presentation_pipeline import PresentationPipeline

__all__ = [
    'ArtifactPipeline',
    'PresentationPipeline',
    'PresentationResult',
    'BatchPresentationResult',
]


def __getattr__(name):
    """Lazy loading of pipeline classes to avoid import errors from dependencies"""
    if name == 'ArtifactPipeline':
        from .orchestrator import ArtifactPipeline
        return ArtifactPipeline
    elif name == 'PresentationPipeline':
        from .presentation_pipeline import PresentationPipeline
        return PresentationPipeline
    elif name == 'PresentationResult':
        from .presentation_pipeline import PresentationResult
        return PresentationResult
    elif name == 'BatchPresentationResult':
        from .presentation_pipeline import BatchPresentationResult
        return BatchPresentationResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

