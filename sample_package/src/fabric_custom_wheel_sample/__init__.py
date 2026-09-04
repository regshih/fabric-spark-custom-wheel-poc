"""Open sample package used to validate Fabric custom-wheel distribution.

It intentionally provides no security or cryptographic claims.
"""

from .provider import SampleTransformer, health, transform

__version__ = "0.1.0"
__all__ = ["SampleTransformer", "health", "transform", "__version__"]
