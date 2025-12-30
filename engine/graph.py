from typing import Any, Dict, List, Optional

from engine.nodes import Node
from engine.profiler import PerformanceProfiler
from engine.validation import EvaluationError


class TariffGraph:
    """
    Graphe de tarification pour l'évaluation des primes.

    Le graphe représente un DAG (Directed Acyclic Graph) de nœuds de calcul.
    L'évaluation se fait de manière récursive avec mise en cache des résultats.

    Attributes:
        nodes: Dictionnaire {nom -> Node} des nœuds du graphe
    """

    def __init__(self, nodes: dict[str, Node]):
        """
        Initialise un graphe de tarification.

        Args:
            nodes: Dictionnaire des nœuds indexés par leur nom
        """
        self.nodes = nodes

    def evaluate(
        self,
        root: str,
        context: Dict[str, Any],
        trace: Optional[Dict] = None,
        node_path: Optional[List[str]] = None,
        profiler: Optional[PerformanceProfiler] = None,
    ):
        """
        Évalue le graphe à partir d'un nœud racine.

        Le graphe est évalué de manière récursive avec mise en cache. En cas d'erreur,
        le chemin complet des dépendances est inclus pour faciliter le debugging.

        Args:
            root: Nom du nœud racine à évaluer (ex: "total_premium")
            context: Contexte contenant les valeurs d'input
                    Exemple: {"driver_age": 30, "brand": "BMW", "density": 800}
            trace: Dictionnaire optionnel pour collecter la trace d'évaluation.
                   Si fourni, la méthode retourne ce dict avec les infos de chaque nœud
                   évalué (valeur, type, chemin).
            node_path: ⚠️ Paramètre interne uniquement, ne pas utiliser directement.
                      Utilisé en interne pour tracer le chemin de dépendances lors d'erreurs.
                      Exemple de chemin: ['total_premium', 'raw_total', 'technical_premium']
            profiler: PerformanceProfiler optionnel pour collecter des statistiques de
                     performance (temps d'évaluation, cache hits/misses par nœud)

        Returns:
            - Si trace is None: La valeur calculée du nœud racine (Decimal)
            - Si trace fourni: Le dictionnaire trace enrichi avec toutes les évaluations

        Raises:
            EvaluationError: En cas d'erreur lors de l'évaluation. L'exception inclut:
                            - node_name: Le nom du nœud en erreur
                            - node_path: Le chemin complet des dépendances
                            - context: Le contexte d'évaluation (pour reproduction)
                            - original_error: L'erreur Python originale
            KeyError: Si le nœud racine n'existe pas dans le graphe

        Examples:
            >>> # Utilisation normale
            >>> result = graph.evaluate("total_premium", {"age": 30, "brand": "BMW"})
            Decimal('525.00')

            >>> # Avec trace pour debugging
            >>> trace = {}
            >>> result = graph.evaluate("total_premium", context, trace=trace)
            >>> print(trace["technical_premium"])
            {'value': Decimal('500'), 'type': 'MultiplyNode', 'path': [...]}

            >>> # Erreur avec chemin de dépendances détaillé
            >>> try:
            ...     graph.evaluate("total_premium", {"age": 17, "brand": "BMW"})
            ... except EvaluationError as e:
            ...     # Message d'erreur enrichi automatiquement:
            ...     # Error evaluating node 'age_factor': 'Value 17 outside all ranges'
            ...     #   Node: age_factor
            ...     #   Path: total_premium -> technical_premium -> age_factor
            ...     #   Context: {'age': 17, 'brand': 'BMW'}
            ...     #   Original error: KeyError: 'Value 17 outside all ranges'
            ...     print(e.node_path)  # ['total_premium', 'technical_premium', 'age_factor']
        """
        if root not in self.nodes:
            available = list(self.nodes.keys())[:10]
            raise KeyError(
                f"Node '{root}' not found in graph. Available nodes: {available}"
                + ("..." if len(self.nodes) > 10 else "")
            )

        cache = {}
        if node_path is None:
            node_path = []

        def eval_node(name: str, current_path: List[str]):
            """
            Évalue un nœud de manière récursive.

            Le current_path trace le chemin de dépendances pour les messages d'erreur.
            Par exemple, si total_premium dépend de raw_total qui dépend de
            technical_premium:
            - Appel 1: eval_node('total_premium', []) -> current_path = []
            - Appel 2: eval_node('raw_total', ['total_premium'])
            - Appel 3: eval_node('technical_premium', ['total_premium', 'raw_total'])

            En cas d'erreur, on voit le chemin complet de dépendances.
            """
            if name in cache:
                if profiler:
                    profiler.record_cache_hit(name)
                return cache[name]

            if profiler:
                profiler.record_cache_miss(name)

            if name not in self.nodes:
                raise EvaluationError(
                    f"Node '{name}' referenced but not found in graph",
                    node_name=name,
                    node_path=current_path,
                    context=context,
                )

            node = self.nodes[name]
            # Ajoute le nœud courant au chemin pour les appels récursifs
            new_path = current_path + [name]

            # Évaluer les dépendances
            try:
                for dep in node.dependencies():
                    eval_node(dep, new_path)
            except Exception as e:
                if not isinstance(e, EvaluationError):
                    raise EvaluationError(
                        f"Error evaluating dependency '{dep}' of node '{name}'",
                        node_name=name,
                        node_path=new_path,
                        context=context,
                        original_error=e,
                    )
                raise

            # Évaluer le nœud lui-même
            try:
                if profiler:
                    profiler.start_node(name)
                val = node.evaluate(context, cache)
                if profiler:
                    profiler.end_node(name)
            except Exception as e:
                if profiler:
                    profiler.end_node(name)
                if not isinstance(e, EvaluationError):
                    raise EvaluationError(
                        f"Error evaluating node '{name}': {str(e)}",
                        node_name=name,
                        node_path=new_path,
                        context=context,
                        original_error=e,
                    )
                raise

            cache[name] = val

            if trace is not None:
                trace[name] = {
                    "value": val,
                    "type": type(node).__name__,
                    "path": new_path,
                }

            return val

        eval_node(root, node_path)
        return cache[root] if trace is None else trace

    def evaluate_batch(
        self,
        root: str,
        contexts: List[Dict[str, Any]],
        collect_errors: bool = False,
    ):
        """
        Évalue le graphe pour plusieurs contextes en batch.

        Cette méthode est optimisée pour traiter de grands volumes de données
        (ex: pricing de portefeuilles entiers). Chaque contexte est évalué
        indépendamment avec son propre cache.

        Args:
            root: Nom du nœud racine à évaluer
            contexts: Liste de dictionnaires de contexte
            collect_errors: Si True, collecte les erreurs au lieu de les lever
                           (utile pour traiter un batch même si certains échouent)

        Returns:
            Si collect_errors=False: Liste des valeurs calculées (même ordre que contexts)
            Si collect_errors=True: Tuple (results, errors) où:
                - results: Liste des valeurs (None pour les lignes en erreur)
                - errors: Liste des exceptions (None pour les lignes réussies)

        Examples:
            >>> contexts = [
            ...     {"age": 30, "brand": "BMW"},
            ...     {"age": 45, "brand": "Audi"},
            ...     {"age": 55, "brand": "Toyota"},
            ... ]
            >>> results = graph.evaluate_batch("total_premium", contexts)
            >>> len(results)
            3

            >>> # Avec gestion d'erreurs
            >>> results, errors = graph.evaluate_batch(
            ...     "total_premium", contexts, collect_errors=True
            ... )
            >>> failed_indices = [i for i, e in enumerate(errors) if e is not None]
        """
        if collect_errors:
            results = []
            errors = []

            for ctx in contexts:
                try:
                    val = self.evaluate(root, ctx)
                    results.append(val)
                    errors.append(None)
                except Exception as e:
                    results.append(None)
                    errors.append(e)

            return results, errors
        else:
            # Mode normal : lève une exception à la première erreur
            return [self.evaluate(root, ctx) for ctx in contexts]
