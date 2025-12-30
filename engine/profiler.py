"""
Module de profiling pour analyser les performances du rating engine.

Ce module permet de collecter des statistiques sur l'évaluation des nœuds
pour identifier les goulots d'étranglement et optimiser les tarifs.
"""

import time
from collections import defaultdict
from typing import Dict


class PerformanceProfiler:
    """
    Collecte des statistiques de performance lors de l'évaluation.

    Mesure le temps d'évaluation de chaque nœud et collecte des statistiques
    sur les accès au cache et les erreurs.

    Attributes:
        enabled: Si False, le profiling n'a aucun overhead
        node_times: Temps cumulé par nœud (en secondes)
        node_calls: Nombre d'appels par nœud
        cache_hits: Nombre de cache hits par nœud
        cache_misses: Nombre de cache misses par nœud

    Examples:
        >>> profiler = PerformanceProfiler()
        >>> # Utilisation avec un graphe
        >>> result = graph.evaluate("total_premium", context, profiler=profiler)
        >>> stats = profiler.get_stats()
        >>> print(f"Nœud le plus lent: {stats['slowest_node']}")
    """

    def __init__(self, enabled: bool = True):
        """
        Initialise le profiler.

        Args:
            enabled: Si True, collecte les statistiques (défaut: True)
        """
        self.enabled = enabled
        self.node_times: Dict[str, float] = defaultdict(float)
        self.node_calls: Dict[str, int] = defaultdict(int)
        self.cache_hits: Dict[str, int] = defaultdict(int)
        self.cache_misses: Dict[str, int] = defaultdict(int)
        self._start_times: Dict[str, float] = {}

    def start_node(self, node_name: str):
        """
        Démarre le chronométrage d'un nœud.

        Args:
            node_name: Nom du nœud à profiler
        """
        if not self.enabled:
            return

        self._start_times[node_name] = time.perf_counter()

    def end_node(self, node_name: str):
        """
        Termine le chronométrage d'un nœud.

        Args:
            node_name: Nom du nœud
        """
        if not self.enabled:
            return

        if node_name in self._start_times:
            elapsed = time.perf_counter() - self._start_times[node_name]
            self.node_times[node_name] += elapsed
            self.node_calls[node_name] += 1
            del self._start_times[node_name]

    def record_cache_hit(self, node_name: str):
        """
        Enregistre un cache hit.

        Args:
            node_name: Nom du nœud
        """
        if not self.enabled:
            return

        self.cache_hits[node_name] += 1

    def record_cache_miss(self, node_name: str):
        """
        Enregistre un cache miss.

        Args:
            node_name: Nom du nœud
        """
        if not self.enabled:
            return

        self.cache_misses[node_name] += 1

    def get_stats(self) -> Dict:
        """
        Retourne les statistiques collectées.

        Returns:
            Dictionnaire contenant:
                - total_time: Temps total d'évaluation (secondes)
                - total_calls: Nombre total d'appels de nœuds
                - nodes: Statistiques par nœud (triées par temps décroissant)
                - slowest_node: Nom du nœud le plus lent
                - most_called_node: Nom du nœud le plus appelé
                - cache_hit_rate: Taux de cache hits global

        Examples:
            >>> stats = profiler.get_stats()
            >>> for node in stats['nodes'][:5]:  # Top 5 des nœuds lents
            ...     print(f"{node['name']}: {node['time_ms']:.2f}ms")
        """
        if not self.enabled:
            return {"enabled": False}

        nodes_stats = []
        for node_name in self.node_times:
            total_time = self.node_times[node_name]
            calls = self.node_calls[node_name]
            hits = self.cache_hits.get(node_name, 0)
            misses = self.cache_misses.get(node_name, 0)
            total_accesses = hits + misses

            nodes_stats.append(
                {
                    "name": node_name,
                    "time_seconds": total_time,
                    "time_ms": total_time * 1000,
                    "calls": calls,
                    "avg_time_ms": (total_time / calls * 1000) if calls > 0 else 0,
                    "cache_hits": hits,
                    "cache_misses": misses,
                    "cache_hit_rate": (hits / total_accesses * 100) if total_accesses > 0 else 0,
                }
            )

        # Trier par temps décroissant
        nodes_stats.sort(key=lambda x: x["time_seconds"], reverse=True)

        total_time = sum(self.node_times.values())
        total_calls = sum(self.node_calls.values())
        total_hits = sum(self.cache_hits.values())
        total_misses = sum(self.cache_misses.values())
        total_accesses = total_hits + total_misses

        return {
            "enabled": True,
            "total_time_seconds": total_time,
            "total_time_ms": total_time * 1000,
            "total_calls": total_calls,
            "total_cache_hits": total_hits,
            "total_cache_misses": total_misses,
            "cache_hit_rate": (total_hits / total_accesses * 100) if total_accesses > 0 else 0,
            "nodes": nodes_stats,
            "slowest_node": nodes_stats[0]["name"] if nodes_stats else None,
            "most_called_node": (
                max(nodes_stats, key=lambda x: x["calls"])["name"] if nodes_stats else None
            ),
        }

    def print_report(self, top_n: int = 10):
        """
        Affiche un rapport de performance formaté.

        Args:
            top_n: Nombre de nœuds à afficher (défaut: 10)

        Examples:
            >>> profiler.print_report(top_n=5)
            Performance Report:
            ==================
            Total time: 0.123s (123.45ms)
            Total calls: 1234
            Cache hit rate: 85.3%

            Top 5 slowest nodes:
            1. technical_premium: 45.2ms (123 calls, 0.37ms avg)
            2. age_factor: 32.1ms (456 calls, 0.07ms avg)
            ...
        """
        stats = self.get_stats()

        if not stats["enabled"]:
            print("Profiling is disabled")
            return

        print("\nPerformance Report:")
        print("=" * 80)
        print(f"Total time: {stats['total_time_seconds']:.3f}s ({stats['total_time_ms']:.2f}ms)")
        print(f"Total calls: {stats['total_calls']}")
        print(f"Cache hit rate: {stats['cache_hit_rate']:.1f}%")
        print(f"\nTop {top_n} slowest nodes:")
        print("-" * 80)

        for i, node in enumerate(stats["nodes"][:top_n], 1):
            print(
                f"{i:2d}. {node['name']:30s}: {node['time_ms']:8.2f}ms "
                f"({node['calls']:5d} calls, {node['avg_time_ms']:6.3f}ms avg, "
                f"cache hit: {node['cache_hit_rate']:5.1f}%)"
            )

        print("=" * 80)

    def reset(self):
        """Réinitialise toutes les statistiques."""
        self.node_times.clear()
        self.node_calls.clear()
        self.cache_hits.clear()
        self.cache_misses.clear()
        self._start_times.clear()
