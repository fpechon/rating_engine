"""
Module de validation pour le rating engine.

Fournit des exceptions personnalisées pour améliorer les messages d'erreur.
"""

from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    """Exception personnalisée pour les erreurs de validation."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        self.field = field
        self.value = value
        super().__init__(message)


class EvaluationError(Exception):
    """Exception enrichie pour les erreurs d'évaluation avec contexte."""

    def __init__(
        self,
        message: str,
        node_name: Optional[str] = None,
        node_path: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        self.node_name = node_name
        self.node_path = node_path or []
        self.context = context or {}
        self.original_error = original_error

        # Construire le message enrichi
        enriched_message = message
        if node_name:
            enriched_message += f"\n  Node: {node_name}"
        if node_path:
            enriched_message += f"\n  Path: {' -> '.join(node_path)}"
        if context:
            enriched_message += (
                f"\n  Context: {dict(list(context.items())[:5])}"  # Premiers 5 items
            )
        if original_error:
            enriched_message += (
                f"\n  Original error: {type(original_error).__name__}: {str(original_error)}"
            )

        super().__init__(enriched_message)
