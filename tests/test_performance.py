"""
Tests de performance et d'optimisation du rating engine.

Ce module teste les optimisations implémentées dans la Phase 2:
- Recherche binaire dans RangeTable
- Évaluation en batch
- Profiling
"""

import pytest
import time
from decimal import Decimal
from engine.tables import RangeTable
from engine.nodes import ConstantNode, InputNode, AddNode, MultiplyNode
from engine.graph import TariffGraph
from engine.profiler import PerformanceProfiler


class TestRangeTableOptimization:
    """Tests de l'optimisation RangeTable avec recherche binaire."""

    def test_range_table_sorted_on_init(self):
        """Test que les ranges sont triés à l'initialisation."""
        rows = [
            {"min": 50, "max": 60, "value": Decimal("3")},
            {"min": 30, "max": 40, "value": Decimal("2")},
            {"min": 10, "max": 20, "value": Decimal("1")},
        ]
        table = RangeTable(rows)

        # Vérifie que les rows sont triés par min
        assert table.rows[0]["min"] == 10
        assert table.rows[1]["min"] == 30
        assert table.rows[2]["min"] == 50

    def test_range_table_sorted_mins_created(self):
        """Test que _sorted_mins est créé correctement."""
        rows = [
            {"min": 10, "max": 20, "value": Decimal("1")},
            {"min": 30, "max": 40, "value": Decimal("2")},
        ]
        table = RangeTable(rows)

        assert table._sorted_mins == [10, 30]

    def test_binary_search_lookup_basic(self):
        """Test que la recherche binaire trouve les bonnes valeurs."""
        rows = [
            {"min": 10, "max": 20, "value": Decimal("1")},
            {"min": 30, "max": 40, "value": Decimal("2")},
            {"min": 50, "max": 60, "value": Decimal("3")},
        ]
        table = RangeTable(rows)

        assert table.lookup(15) == Decimal("1")
        assert table.lookup(35) == Decimal("2")
        assert table.lookup(55) == Decimal("3")

    def test_binary_search_lookup_boundaries(self):
        """Test lookup aux limites des ranges."""
        rows = [
            {"min": 10, "max": 20, "value": Decimal("1")},
            {"min": 21, "max": 30, "value": Decimal("2")},
        ]
        table = RangeTable(rows)

        assert table.lookup(10) == Decimal("1")
        assert table.lookup(20) == Decimal("1")
        assert table.lookup(21) == Decimal("2")
        assert table.lookup(30) == Decimal("2")

    def test_binary_search_lookup_with_gaps(self):
        """Test lookup avec des trous entre les ranges."""
        rows = [
            {"min": 10, "max": 20, "value": Decimal("1")},
            {"min": 30, "max": 40, "value": Decimal("2")},
        ]
        table = RangeTable(rows)

        # Valeur dans un trou -> doit lever KeyError
        with pytest.raises(KeyError, match="outside all ranges"):
            table.lookup(25)

    def test_binary_search_performance_large_table(self):
        """Test de performance avec une grande table (simulation 20k ranges)."""
        # Créer une grande table (simplifié pour le test)
        rows = [
            {"min": i * 10, "max": i * 10 + 9, "value": Decimal(str(i))}
            for i in range(1000)  # 1000 ranges pour le test
        ]
        table = RangeTable(rows)

        # Mesurer le temps de lookup
        start = time.perf_counter()
        for _ in range(1000):
            table.lookup(5005)  # Milieu de la table
        elapsed = time.perf_counter() - start

        # Devrait être très rapide (< 10ms pour 1000 lookups)
        assert elapsed < 0.01, f"Too slow: {elapsed}s for 1000 lookups"

    def test_binary_search_with_default(self):
        """Test que default fonctionne avec la recherche binaire."""
        rows = [
            {"min": 10, "max": 20, "value": Decimal("1")},
        ]
        table = RangeTable(rows, default=Decimal("999"))

        # Valeur hors range doit retourner default
        assert table.lookup(5) == Decimal("999")
        assert table.lookup(25) == Decimal("999")


class TestBatchEvaluation:
    """Tests de l'évaluation en batch."""

    def test_evaluate_batch_basic(self):
        """Test évaluation batch basique."""
        a = ConstantNode("a", Decimal("10"))
        b = InputNode("b")
        sum_node = AddNode("sum", [a, b])

        nodes = {"a": a, "b": b, "sum": sum_node}
        graph = TariffGraph(nodes)

        contexts = [
            {"b": 1},
            {"b": 2},
            {"b": 3},
        ]

        results = graph.evaluate_batch("sum", contexts)

        assert len(results) == 3
        assert results[0] == Decimal("11")
        assert results[1] == Decimal("12")
        assert results[2] == Decimal("13")

    def test_evaluate_batch_preserves_order(self):
        """Test que l'ordre des résultats correspond aux contextes."""
        a = InputNode("a")
        nodes = {"a": a}
        graph = TariffGraph(nodes)

        contexts = [{"a": i} for i in range(100)]
        results = graph.evaluate_batch("a", contexts)

        for i, result in enumerate(results):
            assert result == Decimal(str(i))

    def test_evaluate_batch_with_error_collection(self):
        """Test collect_errors=True."""
        a = InputNode("a")
        nodes = {"a": a}
        graph = TariffGraph(nodes)

        contexts = [
            {"a": 1},  # OK
            {},  # Erreur: 'a' manquant
            {"a": 3},  # OK
        ]

        results, errors = graph.evaluate_batch("a", contexts, collect_errors=True)

        assert len(results) == 3
        assert len(errors) == 3

        # Première et troisième lignes OK
        assert results[0] == Decimal("1")
        assert errors[0] is None

        assert results[2] == Decimal("3")
        assert errors[2] is None

        # Deuxième ligne en erreur
        assert results[1] is None
        assert errors[1] is not None
        assert "Missing input variable" in str(errors[1])

    def test_evaluate_batch_stops_on_first_error_without_collection(self):
        """Test que sans collect_errors, on s'arrête à la première erreur."""
        a = InputNode("a")
        nodes = {"a": a}
        graph = TariffGraph(nodes)

        contexts = [
            {"a": 1},
            {},  # Erreur
            {"a": 3},
        ]

        with pytest.raises(Exception):
            graph.evaluate_batch("a", contexts, collect_errors=False)

    def test_evaluate_batch_large_volume(self):
        """Test performance avec un grand volume."""
        a = ConstantNode("a", Decimal("100"))
        b = InputNode("b")
        c = MultiplyNode("c", [a, b])

        nodes = {"a": a, "b": b, "c": c}
        graph = TariffGraph(nodes)

        # 10000 contextes
        contexts = [{"b": i % 10} for i in range(10000)]

        start = time.perf_counter()
        results = graph.evaluate_batch("c", contexts)
        elapsed = time.perf_counter() - start

        assert len(results) == 10000
        # Devrait être rapide (< 1s pour 10k évaluations simples)
        assert elapsed < 1.0, f"Too slow: {elapsed}s for 10k evaluations"


class TestPerformanceProfiler:
    """Tests du profiler de performance."""

    def test_profiler_enabled_by_default(self):
        """Test que le profiler est activé par défaut."""
        profiler = PerformanceProfiler()
        assert profiler.enabled is True

    def test_profiler_can_be_disabled(self):
        """Test que le profiler peut être désactivé."""
        profiler = PerformanceProfiler(enabled=False)
        assert profiler.enabled is False

    def test_profiler_tracks_node_time(self):
        """Test que le profiler mesure le temps d'évaluation."""
        profiler = PerformanceProfiler()

        profiler.start_node("test_node")
        time.sleep(0.01)  # 10ms
        profiler.end_node("test_node")

        assert "test_node" in profiler.node_times
        assert profiler.node_times["test_node"] >= 0.01
        assert profiler.node_calls["test_node"] == 1

    def test_profiler_accumulates_multiple_calls(self):
        """Test que le profiler cumule les temps sur plusieurs appels."""
        profiler = PerformanceProfiler()

        for _ in range(3):
            profiler.start_node("test_node")
            time.sleep(0.005)  # 5ms
            profiler.end_node("test_node")

        assert profiler.node_calls["test_node"] == 3
        assert profiler.node_times["test_node"] >= 0.015  # 3 * 5ms

    def test_profiler_tracks_cache_hits_and_misses(self):
        """Test que le profiler compte les cache hits/misses."""
        profiler = PerformanceProfiler()

        profiler.record_cache_hit("node_a")
        profiler.record_cache_hit("node_a")
        profiler.record_cache_miss("node_a")

        assert profiler.cache_hits["node_a"] == 2
        assert profiler.cache_misses["node_a"] == 1

    def test_profiler_get_stats_format(self):
        """Test le format des statistiques retournées."""
        profiler = PerformanceProfiler()

        profiler.start_node("node1")
        time.sleep(0.01)
        profiler.end_node("node1")

        profiler.record_cache_hit("node1")
        profiler.record_cache_miss("node1")

        stats = profiler.get_stats()

        assert stats["enabled"] is True
        assert "total_time_seconds" in stats
        assert "total_calls" in stats
        assert "cache_hit_rate" in stats
        assert "nodes" in stats
        assert len(stats["nodes"]) == 1

        node_stats = stats["nodes"][0]
        assert node_stats["name"] == "node1"
        assert "time_ms" in node_stats
        assert "calls" in node_stats
        assert "avg_time_ms" in node_stats
        assert "cache_hit_rate" in node_stats

    def test_profiler_nodes_sorted_by_time(self):
        """Test que les nœuds sont triés par temps décroissant."""
        profiler = PerformanceProfiler()

        profiler.start_node("fast")
        time.sleep(0.001)
        profiler.end_node("fast")

        profiler.start_node("slow")
        time.sleep(0.01)
        profiler.end_node("slow")

        stats = profiler.get_stats()

        # Le nœud le plus lent devrait être en premier
        assert stats["nodes"][0]["name"] == "slow"
        assert stats["nodes"][1]["name"] == "fast"
        assert stats["slowest_node"] == "slow"

    def test_profiler_reset(self):
        """Test que reset efface toutes les statistiques."""
        profiler = PerformanceProfiler()

        profiler.start_node("node1")
        profiler.end_node("node1")
        profiler.record_cache_hit("node1")

        assert len(profiler.node_times) > 0

        profiler.reset()

        assert len(profiler.node_times) == 0
        assert len(profiler.node_calls) == 0
        assert len(profiler.cache_hits) == 0
        assert len(profiler.cache_misses) == 0

    def test_profiler_no_overhead_when_disabled(self):
        """Test que le profiler désactivé n'a pas d'overhead."""
        profiler = PerformanceProfiler(enabled=False)

        # Ces appels ne devraient rien faire
        profiler.start_node("test")
        profiler.end_node("test")
        profiler.record_cache_hit("test")

        assert len(profiler.node_times) == 0
        assert len(profiler.cache_hits) == 0

        stats = profiler.get_stats()
        assert stats["enabled"] is False
