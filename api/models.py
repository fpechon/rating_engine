"""
Modèles Pydantic pour l'API REST.

Définit les schémas de requêtes et réponses pour tous les endpoints.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PricingRequest(BaseModel):
    """
    Requête pour évaluer un tarif (single pricing).

    Attributes:
        context: Dictionnaire des variables d'entrée (age, brand, etc.)
        target_node: Nom du nœud à évaluer (par défaut: total_premium)
        include_trace: Si True, inclut la trace complète de l'évaluation
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "context": {
                    "driver_age": 35,
                    "brand": "BMW",
                    "density": 1200,
                    "neighbourhood_id": "19582",
                },
                "target_node": "total_premium",
                "include_trace": False,
            }
        }
    )

    context: Dict[str, Any] = Field(
        ..., description="Variables d'entrée pour l'évaluation du tarif"
    )
    target_node: str = Field(
        default="total_premium", description="Nom du nœud à évaluer dans le graphe de tarification"
    )
    include_trace: bool = Field(
        default=False, description="Inclure la trace complète de l'évaluation dans la réponse"
    )


class PricingResponse(BaseModel):
    """
    Réponse d'une évaluation de tarif.

    Attributes:
        result: Résultat de l'évaluation (typiquement une prime)
        target_node: Nœud qui a été évalué
        context: Contexte d'évaluation utilisé
        trace: Trace optionnelle de l'évaluation
        metadata: Métadonnées du tarif utilisé
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "result": "429.18",
                "target_node": "total_premium",
                "context": {"driver_age": 35, "brand": "BMW"},
                "metadata": {"product": "MOTOR_PRIVATE", "version": "2024_09", "currency": "EUR"},
            }
        }
    )

    result: Optional[str] = Field(
        None,
        description="Résultat de l'évaluation (converti en string pour préserver la précision)",
    )
    target_node: str = Field(..., description="Nœud évalué")
    context: Dict[str, Any] = Field(..., description="Contexte d'évaluation")
    trace: Optional[Dict[str, Any]] = Field(
        None, description="Trace complète de l'évaluation (si demandée)"
    )
    metadata: Dict[str, Any] = Field(..., description="Métadonnées du tarif")


class BatchPricingRequest(BaseModel):
    """
    Requête pour évaluer plusieurs contextes en batch.

    Attributes:
        contexts: Liste des contextes à évaluer
        target_node: Nom du nœud à évaluer
        collect_errors: Si True, continue même en cas d'erreur et retourne les erreurs
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "contexts": [
                    {"driver_age": 25, "brand": "BMW"},
                    {"driver_age": 45, "brand": "Toyota"},
                    {"driver_age": 65, "brand": "Audi"},
                ],
                "target_node": "total_premium",
                "collect_errors": True,
            }
        }
    )

    contexts: List[Dict[str, Any]] = Field(
        ..., min_length=1, description="Liste des contextes à évaluer"
    )
    target_node: str = Field(default="total_premium", description="Nom du nœud à évaluer")
    collect_errors: bool = Field(
        default=True, description="Continuer l'évaluation même en cas d'erreur"
    )


class BatchPricingResult(BaseModel):
    """
    Résultat individuel dans un batch.

    Attributes:
        row_index: Index de la ligne dans le batch
        result: Résultat de l'évaluation (ou None si erreur)
        context: Contexte utilisé
        error: Message d'erreur (si erreur)
    """

    row_index: int = Field(..., description="Index de la ligne")
    result: Optional[str] = Field(None, description="Résultat (ou None si erreur)")
    context: Dict[str, Any] = Field(..., description="Contexte d'évaluation")
    error: Optional[str] = Field(None, description="Message d'erreur (si erreur)")


class BatchPricingResponse(BaseModel):
    """
    Réponse d'un batch pricing.

    Attributes:
        results: Liste des résultats
        total_count: Nombre total de contextes évalués
        success_count: Nombre de succès
        error_count: Nombre d'erreurs
        target_node: Nœud évalué
        metadata: Métadonnées du tarif
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "results": [
                    {"row_index": 0, "result": "720.00", "context": {"driver_age": 25}},
                    {"row_index": 1, "result": "450.00", "context": {"driver_age": 45}},
                ],
                "total_count": 2,
                "success_count": 2,
                "error_count": 0,
                "target_node": "total_premium",
                "metadata": {"product": "MOTOR_PRIVATE", "version": "2024_09"},
            }
        }
    )

    results: List[BatchPricingResult] = Field(..., description="Liste des résultats")
    total_count: int = Field(..., description="Nombre total de contextes")
    success_count: int = Field(..., description="Nombre de succès")
    error_count: int = Field(..., description="Nombre d'erreurs")
    target_node: str = Field(..., description="Nœud évalué")
    metadata: Dict[str, Any] = Field(..., description="Métadonnées du tarif")


class HealthResponse(BaseModel):
    """Réponse du endpoint de health check."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "tariff_loaded": True,
                "tariff_info": {
                    "product": "MOTOR_PRIVATE",
                    "version": "2024_09",
                    "nodes_count": 42,
                },
            }
        }
    )

    status: str = Field(..., description="État de l'API (healthy/unhealthy)")
    version: str = Field(..., description="Version de l'API")
    tariff_loaded: bool = Field(..., description="Si un tarif est chargé")
    tariff_info: Optional[Dict[str, Any]] = Field(
        None, description="Informations sur le tarif chargé"
    )


class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Node 'total_premium' not found in graph",
                "error_type": "NodeNotFoundError",
                "context": {"target_node": "total_premium"},
            }
        }
    )

    detail: str = Field(..., description="Message d'erreur détaillé")
    error_type: str = Field(..., description="Type d'erreur")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexte additionnel de l'erreur")
