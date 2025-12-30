"""
Application FastAPI principale pour le moteur de tarification.

Cette API expose des endpoints pour évaluer des tarifs de manière synchrone,
en single ou en batch.
"""

import os
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from engine.graph import TariffGraph
from engine.loader import TariffLoader
from engine.metadata import TariffMetadata
from engine.tables import load_exact_table, load_range_table

from .models import (
    BatchPricingRequest,
    BatchPricingResponse,
    BatchPricingResult,
    ErrorResponse,
    HealthResponse,
    PricingRequest,
    PricingResponse,
)

# Version de l'API
API_VERSION = "0.1.0"

# Variables globales pour le tarif chargé
_graph: Optional[TariffGraph] = None
_metadata: Optional[TariffMetadata] = None


def load_tariff_from_env() -> tuple[TariffGraph, TariffMetadata]:
    """
    Charge un tarif depuis les variables d'environnement.

    Variables d'environnement:
        TARIFF_PATH: Chemin vers le fichier tariff.yaml
        TABLES_DIR: Répertoire contenant les tables CSV

    Returns:
        Tuple (graph, metadata)

    Raises:
        ValueError: Si les variables d'environnement ne sont pas définies
        FileNotFoundError: Si les fichiers n'existent pas
    """
    tariff_path = os.getenv("TARIFF_PATH")
    tables_dir = os.getenv("TABLES_DIR")

    if not tariff_path:
        # Par défaut, charger le tarif motor
        project_root = Path(__file__).parent.parent
        tariff_path = str(project_root / "tariffs/motor_private/2024_09/tariff.yaml")
        tables_dir = str(project_root / "tariffs/motor_private/2024_09/tables")

    if not Path(tariff_path).exists():
        raise FileNotFoundError(f"Tariff file not found: {tariff_path}")

    # Charger les tables
    tables_path = Path(tables_dir) if tables_dir else Path(tariff_path).parent / "tables"

    tables = {}
    if tables_path.exists():
        # Auto-détection : charger toutes les tables CSV du répertoire
        # On essaie d'abord en range, puis en exact si ça échoue
        for csv_file in tables_path.glob("*.csv"):
            table_name = csv_file.stem  # nom sans extension
            try:
                # Essayer en range table (pour les tables avec min/max)
                tables[table_name] = load_range_table(str(csv_file))
                print(f"  Loaded range table: {table_name}")
            except Exception:
                # Sinon, essayer en exact table
                try:
                    # Détecter les colonnes key/value communes
                    import pandas as pd

                    df = pd.read_csv(csv_file, nrows=1)
                    cols = df.columns.tolist()

                    if "neighbourhood_id" in cols:
                        # Table zoning spéciale
                        tables[table_name] = load_exact_table(
                            str(csv_file),
                            key_column="neighbourhood_id",
                            value_column="zone",
                            key_type=int,
                        )
                    elif "key" in cols and "value" in cols:
                        tables[table_name] = load_exact_table(
                            str(csv_file),
                            key_column="key",
                            value_column="value",
                        )
                    elif "key" in cols and "factor" in cols:
                        tables[table_name] = load_exact_table(
                            str(csv_file),
                            key_column="key",
                            value_column="factor",
                        )
                    else:
                        # Par défaut: première colonne = key, deuxième = value
                        tables[table_name] = load_exact_table(
                            str(csv_file),
                            key_column=cols[0],
                            value_column=cols[1],
                        )
                    print(f"  Loaded exact table: {table_name}")
                except Exception as e:
                    print(f"  ⚠️  Could not load table {table_name}: {e}")

    # Charger le tarif
    loader = TariffLoader(tables=tables)
    nodes = loader.load(tariff_path)
    graph = TariffGraph(nodes)

    # Charger les métadonnées
    from engine.metadata import load_metadata_from_file

    metadata = load_metadata_from_file(tariff_path)

    return graph, metadata


# Créer l'application FastAPI
app = FastAPI(
    title="Rating Engine API",
    description=(
        "API REST pour évaluer des tarifs d'assurance de manière déclarative. "
        "Supporte l'évaluation single et batch avec traçabilité complète."
    ),
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configuration CORS (à ajuster selon vos besoins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production: spécifier les origins autorisées
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Charger le tarif au démarrage de l'API."""
    global _graph, _metadata
    try:
        _graph, _metadata = load_tariff_from_env()
        print(f"✓ Tariff loaded: {_metadata.product} v{_metadata.version}")
        print(f"  Nodes count: {len(_graph.nodes)}")
    except Exception as e:
        print(f"❌ Failed to load tariff: {e}")
        print("  API will start but pricing endpoints will fail until a tariff is loaded")


@app.get("/", tags=["Root"])
async def root():
    """Page d'accueil de l'API."""
    return {
        "message": "Rating Engine API",
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
    description="Vérifie l'état de l'API et du tarif chargé",
)
async def health_check():
    """Endpoint de health check."""
    tariff_info = None
    if _metadata and _graph:
        tariff_info = {
            "product": _metadata.product,
            "version": _metadata.version,
            "currency": _metadata.currency,
            "nodes_count": len(_graph.nodes),
        }

    return HealthResponse(
        status="healthy" if _graph is not None else "unhealthy",
        version=API_VERSION,
        tariff_loaded=_graph is not None,
        tariff_info=tariff_info,
    )


@app.get(
    "/metadata",
    tags=["Metadata"],
    summary="Get tariff metadata",
    description="Retourne les métadonnées du tarif chargé",
)
async def get_metadata():
    """Retourne les métadonnées du tarif."""
    if _metadata is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No tariff loaded"
        )

    return _metadata.to_dict()


@app.post(
    "/evaluate",
    response_model=PricingResponse,
    tags=["Pricing"],
    summary="Single pricing",
    description="Évalue un tarif pour un contexte donné",
    responses={
        200: {"description": "Évaluation réussie"},
        400: {"model": ErrorResponse, "description": "Erreur dans le contexte ou la requête"},
        503: {"model": ErrorResponse, "description": "Aucun tarif chargé"},
    },
)
async def evaluate(request: PricingRequest):
    """
    Évalue un tarif pour un contexte donné.

    Le contexte doit contenir toutes les variables d'entrée nécessaires
    (ex: driver_age, brand, density, etc.).

    Returns:
        PricingResponse: Résultat de l'évaluation avec métadonnées
    """
    if _graph is None or _metadata is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No tariff loaded"
        )

    try:
        # Évaluer avec ou sans trace
        if request.include_trace:
            trace = {}
            _graph.evaluate(request.target_node, request.context, trace=trace)
            result = trace[request.target_node]["value"]

            # Convertir les Decimal en string dans la trace
            trace_str = _convert_decimals_to_str(trace)
        else:
            trace_str = None
            result = _graph.evaluate(request.target_node, request.context)

        # Convertir le résultat en string pour préserver la précision
        result_str = str(result) if result is not None else None

        return PricingResponse(
            result=result_str,
            target_node=request.target_node,
            context=request.context,
            trace=trace_str,
            metadata=_metadata.to_dict(),
        )

    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required input: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post(
    "/evaluate/batch",
    response_model=BatchPricingResponse,
    tags=["Pricing"],
    summary="Batch pricing",
    description="Évalue un tarif pour plusieurs contextes en une seule requête",
    responses={
        200: {"description": "Évaluation batch réussie"},
        400: {"model": ErrorResponse, "description": "Erreur dans la requête"},
        503: {"model": ErrorResponse, "description": "Aucun tarif chargé"},
    },
)
async def evaluate_batch(request: BatchPricingRequest):
    """
    Évalue un tarif pour plusieurs contextes en batch.

    Beaucoup plus performant que de faire des requêtes individuelles.
    Peut continuer même en cas d'erreur sur certains contextes si collect_errors=True.

    Returns:
        BatchPricingResponse: Résultats de toutes les évaluations
    """
    if _graph is None or _metadata is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No tariff loaded"
        )

    try:
        # Évaluer en batch
        if request.collect_errors:
            results, errors = _graph.evaluate_batch(
                request.target_node, request.contexts, collect_errors=True
            )
        else:
            results = _graph.evaluate_batch(
                request.target_node, request.contexts, collect_errors=False
            )
            errors = [None] * len(results)

        # Construire la réponse
        batch_results = []
        success_count = 0
        error_count = 0

        for i, (result, context, error) in enumerate(zip(results, request.contexts, errors)):
            if error is None and result is not None:
                success_count += 1
                batch_results.append(
                    BatchPricingResult(row_index=i, result=str(result), context=context, error=None)
                )
            else:
                error_count += 1
                batch_results.append(
                    BatchPricingResult(
                        row_index=i,
                        result=None,
                        context=context,
                        error=str(error) if error else "Unknown error",
                    )
                )

        return BatchPricingResponse(
            results=batch_results,
            total_count=len(request.contexts),
            success_count=success_count,
            error_count=error_count,
            target_node=request.target_node,
            metadata=_metadata.to_dict(),
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def _convert_decimals_to_str(obj):
    """Convertit récursivement les Decimal en string."""
    if isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: _convert_decimals_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals_to_str(v) for v in obj]
    return obj


# Point d'entrée pour uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
