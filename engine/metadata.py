"""
Module de gestion des métadonnées de tarifs et export de traces.

Ce module fournit des utilitaires pour:
- Extraire et valider les métadonnées de tarifs
- Exporter les traces d'évaluation en JSON/CSV
- Gérer le versionnage des tarifs
"""

import json
import csv
from pathlib import Path
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime


class TariffMetadata:
    """
    Métadonnées d'un tarif.

    Attributes:
        product: Nom du produit (ex: "MOTOR_PRIVATE")
        version: Version du tarif (ex: "2024_09")
        currency: Devise (ex: "EUR")
        effective_date: Date d'effet optionnelle
        author: Auteur optionnel
        description: Description optionnelle
        changelog: Historique des modifications optionnel
        custom: Métadonnées custom additionnelles

    Examples:
        >>> metadata = TariffMetadata(
        ...     product="MOTOR_PRIVATE",
        ...     version="2024_09",
        ...     currency="EUR",
        ...     effective_date="2024-09-01",
        ...     author="Actuarial Team"
        ... )
        >>> metadata.to_dict()
    """

    def __init__(
        self,
        product: str,
        version: str,
        currency: str,
        effective_date: Optional[str] = None,
        author: Optional[str] = None,
        description: Optional[str] = None,
        changelog: Optional[List[Dict]] = None,
        **custom
    ):
        """
        Initialise les métadonnées.

        Args:
            product: Nom du produit
            version: Version du tarif
            currency: Devise
            effective_date: Date d'effet (format ISO: YYYY-MM-DD)
            author: Auteur du tarif
            description: Description
            changelog: Historique des modifications
            **custom: Métadonnées additionnelles
        """
        self.product = product
        self.version = version
        self.currency = currency
        self.effective_date = effective_date
        self.author = author
        self.description = description
        self.changelog = changelog or []
        self.custom = custom

    @classmethod
    def from_yaml_data(cls, data: Dict[str, Any]) -> "TariffMetadata":
        """
        Crée des métadonnées depuis les données YAML.

        Args:
            data: Dictionnaire parsé depuis YAML

        Returns:
            Instance de TariffMetadata

        Raises:
            ValueError: Si des champs obligatoires manquent

        Examples:
            >>> data = {
            ...     "product": "MOTOR_PRIVATE",
            ...     "version": "2024_09",
            ...     "currency": "EUR",
            ...     "metadata": {
            ...         "effective_date": "2024-09-01",
            ...         "author": "John Doe"
            ...     }
            ... }
            >>> metadata = TariffMetadata.from_yaml_data(data)
        """
        if "product" not in data:
            raise ValueError("Tariff YAML must contain 'product'")
        if "version" not in data:
            raise ValueError("Tariff YAML must contain 'version'")
        if "currency" not in data:
            raise ValueError("Tariff YAML must contain 'currency'")

        # Métadonnées enrichies optionnelles
        meta = data.get("metadata", {})

        return cls(
            product=data["product"],
            version=data["version"],
            currency=data["currency"],
            effective_date=meta.get("effective_date"),
            author=meta.get("author"),
            description=meta.get("description"),
            changelog=meta.get("changelog"),
            **{k: v for k, v in meta.items()
               if k not in ["effective_date", "author", "description", "changelog"]}
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit en dictionnaire.

        Returns:
            Dictionnaire avec toutes les métadonnées
        """
        result = {
            "product": self.product,
            "version": self.version,
            "currency": self.currency,
        }

        if self.effective_date:
            result["effective_date"] = self.effective_date
        if self.author:
            result["author"] = self.author
        if self.description:
            result["description"] = self.description
        if self.changelog:
            result["changelog"] = self.changelog

        # Ajouter métadonnées custom
        result.update(self.custom)

        return result

    def __repr__(self):
        return f"TariffMetadata(product={self.product!r}, version={self.version!r})"


def export_trace_to_json(
    trace: Dict[str, Any],
    output_path: str,
    metadata: Optional[TariffMetadata] = None,
    context: Optional[Dict[str, Any]] = None,
    pretty: bool = True
) -> None:
    """
    Exporte une trace d'évaluation en JSON.

    Args:
        trace: Dictionnaire de trace retourné par graph.evaluate()
        output_path: Chemin du fichier JSON de sortie
        metadata: Métadonnées du tarif optionnelles
        context: Contexte d'évaluation optionnel
        pretty: Si True, format indenté pour lisibilité

    Examples:
        >>> trace = {}
        >>> result = graph.evaluate("total_premium", context, trace=trace)
        >>> export_trace_to_json(
        ...     trace,
        ...     "evaluation_trace.json",
        ...     metadata=metadata,
        ...     context=context
        ... )
    """
    # Convertir les Decimal en float pour JSON
    def decimal_to_float(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: decimal_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [decimal_to_float(v) for v in obj]
        return obj

    # Préparer les données
    data = {
        "timestamp": datetime.now().isoformat(),
        "trace": decimal_to_float(trace),
    }

    if metadata:
        data["metadata"] = metadata.to_dict()

    if context:
        data["context"] = decimal_to_float(context)

    # Écrire le fichier
    with open(output_path, 'w') as f:
        if pretty:
            json.dump(data, f, indent=2)
        else:
            json.dump(data, f)


def export_trace_to_csv(
    trace: Dict[str, Any],
    output_path: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Exporte une trace d'évaluation en CSV.

    Le CSV contient une ligne par nœud évalué avec ses informations.

    Args:
        trace: Dictionnaire de trace retourné par graph.evaluate()
        output_path: Chemin du fichier CSV de sortie
        context: Contexte d'évaluation optionnel (ajouté en colonnes)

    Examples:
        >>> trace = {}
        >>> result = graph.evaluate("total_premium", context, trace=trace)
        >>> export_trace_to_csv(trace, "evaluation_trace.csv", context=context)
    """
    # Colonnes du CSV
    fieldnames = ["node_name", "node_type", "value", "path"]

    # Ajouter colonnes de contexte si fourni
    if context:
        fieldnames.extend([f"context_{k}" for k in context.keys()])

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for node_name, info in trace.items():
            row = {
                "node_name": node_name,
                "node_type": info.get("type", ""),
                "value": str(info.get("value", "")),
                "path": " -> ".join(info.get("path", [])),
            }

            # Ajouter valeurs de contexte
            if context:
                for k, v in context.items():
                    row[f"context_{k}"] = str(v)

            writer.writerow(row)


def export_batch_results(
    results: List[Any],
    contexts: List[Dict[str, Any]],
    output_path: str,
    errors: Optional[List[Optional[Exception]]] = None
) -> None:
    """
    Exporte les résultats d'un batch evaluation en CSV.

    Args:
        results: Liste des résultats (retournés par evaluate_batch)
        contexts: Liste des contextes correspondants
        output_path: Chemin du fichier CSV de sortie
        errors: Liste optionnelle des erreurs (si collect_errors=True)

    Examples:
        >>> contexts = [{"age": 30}, {"age": 45}, {"age": 60}]
        >>> results = graph.evaluate_batch("premium", contexts)
        >>> export_batch_results(results, contexts, "batch_results.csv")

        >>> # Avec gestion d'erreurs
        >>> results, errors = graph.evaluate_batch("premium", contexts, collect_errors=True)
        >>> export_batch_results(results, contexts, "batch_results.csv", errors=errors)
    """
    if len(results) != len(contexts):
        raise ValueError("Results and contexts must have the same length")

    if errors and len(errors) != len(results):
        raise ValueError("Errors list must have the same length as results")

    # Déterminer toutes les colonnes de contexte
    context_keys = set()
    for ctx in contexts:
        context_keys.update(ctx.keys())
    context_keys = sorted(context_keys)

    # Colonnes
    fieldnames = ["row_index", "result"]
    if errors:
        fieldnames.append("error")
    fieldnames.extend(context_keys)

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, (result, ctx) in enumerate(zip(results, contexts)):
            row = {
                "row_index": i,
                "result": str(result) if result is not None else "",
            }

            if errors:
                error = errors[i]
                row["error"] = str(error) if error else ""

            # Ajouter colonnes de contexte
            for key in context_keys:
                row[key] = str(ctx.get(key, ""))

            writer.writerow(row)


def load_metadata_from_file(tariff_path: str) -> TariffMetadata:
    """
    Charge les métadonnées depuis un fichier YAML de tarif.

    Args:
        tariff_path: Chemin vers le fichier tariff.yaml

    Returns:
        Instance de TariffMetadata

    Examples:
        >>> metadata = load_metadata_from_file("tariffs/motor/2024_09/tariff.yaml")
        >>> print(metadata.product, metadata.version)
    """
    import yaml

    with open(tariff_path) as f:
        data = yaml.safe_load(f)

    return TariffMetadata.from_yaml_data(data)
