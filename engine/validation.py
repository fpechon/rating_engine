"""
Module de validation pour le rating engine.
Fournit des fonctions pour valider les inputs et améliorer les messages d'erreur.
"""
from decimal import Decimal
from typing import Any, Dict, Optional, List, Union


class ValidationError(Exception):
    """Exception personnalisée pour les erreurs de validation."""
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        self.field = field
        self.value = value
        super().__init__(message)


class InputSpec:
    """Spécification pour un input attendu."""
    def __init__(
        self,
        name: str,
        dtype: type,
        required: bool = True,
        min_value: Optional[Union[int, float, Decimal]] = None,
        max_value: Optional[Union[int, float, Decimal]] = None,
        allowed_values: Optional[List[Any]] = None,
        description: Optional[str] = None,
    ):
        self.name = name
        self.dtype = dtype
        self.required = required
        self.min_value = min_value
        self.max_value = max_value
        self.allowed_values = allowed_values
        self.description = description


class ContextValidator:
    """Validateur de contexte pour vérifier les inputs avant l'évaluation."""

    def __init__(self, specs: List[InputSpec]):
        self.specs = {spec.name: spec for spec in specs}

    def validate(self, context: Dict[str, Any]) -> None:
        """
        Valide un contexte d'évaluation.

        Args:
            context: Dictionnaire des valeurs d'input

        Raises:
            ValidationError: Si la validation échoue
        """
        errors = []

        # Vérifier les champs manquants
        for name, spec in self.specs.items():
            if spec.required and name not in context:
                errors.append(
                    f"Missing required input '{name}'"
                    + (f": {spec.description}" if spec.description else "")
                )

        # Vérifier les types et ranges
        for name, value in context.items():
            if name not in self.specs:
                continue  # Inputs non spécifiés sont acceptés

            spec = self.specs[name]

            # Ignorer None si non requis
            if value is None:
                if spec.required:
                    errors.append(f"Input '{name}' cannot be None (required field)")
                continue

            # Vérifier le type
            if spec.dtype in (int, float, Decimal):
                try:
                    if spec.dtype == Decimal:
                        value = Decimal(str(value))
                    else:
                        value = spec.dtype(value)
                except (ValueError, TypeError):
                    errors.append(
                        f"Input '{name}' has invalid type: expected {spec.dtype.__name__}, got {type(value).__name__}"
                    )
                    continue

                # Vérifier les ranges
                if spec.min_value is not None and value < spec.min_value:
                    errors.append(
                        f"Input '{name}' value {value} is below minimum {spec.min_value}"
                    )
                if spec.max_value is not None and value > spec.max_value:
                    errors.append(
                        f"Input '{name}' value {value} exceeds maximum {spec.max_value}"
                    )

            elif spec.dtype == str:
                if not isinstance(value, str):
                    errors.append(
                        f"Input '{name}' must be a string, got {type(value).__name__}"
                    )
                    continue

            # Vérifier les valeurs autorisées
            if spec.allowed_values is not None and value not in spec.allowed_values:
                errors.append(
                    f"Input '{name}' value '{value}' not in allowed values: {spec.allowed_values}"
                )

        if errors:
            raise ValidationError(
                "Context validation failed:\n  - " + "\n  - ".join(errors)
            )

    def get_spec(self, name: str) -> Optional[InputSpec]:
        """Retourne la spécification pour un input donné."""
        return self.specs.get(name)


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
            enriched_message += f"\n  Context: {dict(list(context.items())[:5])}"  # Premiers 5 items
        if original_error:
            enriched_message += f"\n  Original error: {type(original_error).__name__}: {str(original_error)}"

        super().__init__(enriched_message)
