"""Integration framework for external services."""

from .base import BaseIntegration
from .registry import IntegrationRegistry

__all__ = ["BaseIntegration", "IntegrationRegistry"]
