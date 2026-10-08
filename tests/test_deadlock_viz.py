"""
Deadlock görselleştirme testleri — senaryo stepper'ları, yerleşim, JSON ve
headless pygame render.

Çalıştır: PYTHONPATH=. pytest tests/test_deadlock_viz.py -v
"""

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

from core.deadlock import ResourceAllocationGraph
from visualization.deadlock_scenario import (
    BUILTIN_BANKER_SCENARIOS,
    BUILTIN_RAG_SCENARIOS,
    BankerScenario,
    BankerStepper,
    ProcessSpec,
    RAGEvent,
    RAGScenario,
    RAGStepper,
    ResourceSpec,
    circular_layout,
    load_deadlock_scenario,
    save_banker_scenario,
    save_rag_scenario,
    scenario_node_order,
)

EXAMPLES = Path(__file__).parent.parent / "examples"


def _scenario(name: str) -> RAGScenario:
    return next(s for s in BUILTIN_RAG_SCENARIOS if s.name.startswith(name))


def _two_cycle() -> RAGScenario:
    return RAGScenario(
        name="t",
        processes=[ProcessSpec(1, "A"), ProcessSpec(2, "B")],
        resources=[ResourceSpec(1, "X"), ResourceSpec(2, "Y")],
        events=[
            RAGEvent("assign", 1, 1),
            RAGEvent("assign", 2, 2),
            RAGEvent("request", 1, 2),
            RAGEvent("request", 2, 1),
        ],
    )


# ===========================================================================
# core.deadlock eklemeleri
# ===========================================================================

class TestRAGQueries:
    def test_cancel_request_removes_edge(self):
        rag = ResourceAllocationGraph()
        rag.add_process(1)
        rag.add_resource(1, "X", 1)
        rag.request_edge(1, 1)
        rag.cancel_request(1, 1)
        assert rag.get_requested_resources(1) == set()

    def test_cancel_unknown_request_is_noop(self):
        rag = ResourceAllocationGraph()
        rag.cancel_request(99, 1)  # hata fırlatmamalı

    def test_deadlock_edges_cover_full_cycle(self):
        stepper = RAGStepper(_two_cycle())
        while stepper.forward():
            pass
        assert stepper.rag.get_deadlock_edges() == {
            ("request", 1, 2), ("request", 2, 1),
            ("assignment", 1, 1), ("assignment", 2, 2),
        }

    def test_deadlock_edges_exclude_non_cycle_edges(self):
        sc = _two_cycle()
        sc.processes.append(ProcessSpec(3, "C"))
        sc.events.append(RAGEvent("request", 3, 1))  # P3 de bekliyor ama döngüde değil
        stepper = RAGStepper(sc)
        while stepper.forward():
            pass
        edges = stepper.rag.get_deadlock_edges()
        assert ("request", 3, 1) not in edges
        assert stepper.deadlocked == [1, 2]

    def test_no_deadlock_no_edges(self):
        stepper = RAGStepper(_two_cycle())
        stepper.forward()
        assert stepper.rag.get_deadlock_edges() == set()

    def test_wait_for_graph_is_copy(self):
        stepper = RAGStepper(_two_cycle())
        while stepper.forward():
            pass
        wf = stepper.rag.get_wait_for_graph()
        assert wf == {1: {2}, 2: {1}}
        wf[1].clear()
        assert stepper.rag.get_wait_for_graph()[1] == {2}


# ===========================================================================
# RAGStepper
# ===========================================================================

class TestRAGStepper:
    def test_starts_empty(self):
        st = RAGStepper(_two_cycle())
        assert st.step == 0
        assert st.last_event is None
        assert st.deadlocked == []

    def test_deadlock_appears_only_on_last_step(self):
        st = RAGStepper(_two_cycle())
        history = []
        while st.forward():
            history.append(st.deadlocked)
        assert history == [[], [], [], [1, 2]]
        assert st.at_end
        assert not st.forward()

    def test_back_restores_previous_state(self):
        st = RAGStepper(_two_cycle())
        while st.forward():
            pass
        assert st.back()
        assert st.step == 3
        assert st.deadlocked == []
        assert st.rag.get_requested_resources(2) == set()

    def test_back_at_start_returns_false(self):
        assert not RAGStepper(_two_cycle()).back()

    def test_reset(self):
        st = RAGStepper(_two_cycle())
        st.forward()
        st.forward()
        st.reset()
        assert st.step == 0
        assert st.rag.get_held_resources(1) == set()

    def test_assign_consumes_request_edge(self):
        sc = RAGScenario(
            "t", [ProcessSpec(1, "A")], [ResourceSpec(1, "X")],
            [RAGEvent("request", 1, 1), RAGEvent("assign", 1, 1)],
        )
        st = RAGStepper(sc)
        st.forward()
        assert st.rag.get_requested_resources(1) == {1}
        st.forward()
        assert st.rag.get_requested_resources(1) == set()
        assert st.rag.get_held_resources(1) == {1}
        assert st.rag.get_resource(1).available_instances == 0

    def test_release_frees_instance(self):
        sc = RAGScenario(
            "t", [ProcessSpec(1, "A")], [ResourceSpec(1, "X", 2)],
            [RAGEvent("assign", 1, 1), RAGEvent("release", 1, 1)],
        )
        st = RAGStepper(sc)
        st.forward()
        assert st.rag.get_resource(1).available_instances == 1
        st.forward()
        assert st.rag.get_resource(1).available_instances == 2

    def test_invalid_assign_rejected_at_construction(self):
        sc = RAGScenario(
            "t", [ProcessSpec(1, "A"), ProcessSpec(2, "B")], [ResourceSpec(1, "X")],
            [RAGEvent("assign", 1, 1), RAGEvent("assign", 2, 1)],
        )
        with pytest.raises(ValueError, match="boş instance yok"):
            RAGStepper(sc)

    def test_unknown_process_rejected(self):
        sc = RAGScenario("t", [], [ResourceSpec(1, "X")], [RAGEvent("request", 7, 1)])
        with pytest.raises(ValueError, match="P7"):
            RAGStepper(sc)

    def test_unknown_action_rejected(self):
        sc = RAGScenario(
            "t", [ProcessSpec(1, "A")], [ResourceSpec(1, "X")],
            [RAGEvent("explode", 1, 1)],  # type: ignore[arg-type]
        )
        with pytest.raises(ValueError, match="Geçersiz aksiyon"):
            RAGStepper(sc)


class TestBuiltinRAGScenarios:
    @pytest.mark.parametrize("scenario", BUILTIN_RAG_SCENARIOS, ids=lambda s: s.name)
    def test_all_builtins_replay_without_error(self, scenario):
        st = RAGStepper(scenario)
        while st.forward():
            pass
        assert st.at_end

    def test_dining_philosophers_deadlocks_then_recovers(self):
        st = RAGStepper(_scenario("Dining"))
        for _ in range(8):
            st.forward()
        assert st.deadlocked == [1, 2, 3, 4]
        while st.forward():
            pass
        assert st.deadlocked == []

    def test_chain_never_deadlocks(self):
        st = RAGStepper(_scenario("Bekleme zinciri"))
        assert st.deadlocked == []
        while st.forward():
            assert st.deadlocked == []

    def test_two_process_cycle_ends_in_deadlock(self):
        st = RAGStepper(_scenario("İki process"))
        while st.forward():
            pass
        assert st.deadlocked == [1, 2]


# ===========================================================================
# BankerStepper
# ===========================================================================

class TestBankerStepper:
    def test_silberschatz_verdicts(self):
        st = BankerStepper(BUILTIN_BANKER_SCENARIOS[0])
        while st.forward():
            pass
        assert [o.verdict for o in st.outcomes] == [
            "granted", "insufficient", "unsafe", "exceeds_need", "granted",
        ]

    def test_initial_state_is_safe(self):
        st = BankerStepper(BUILTIN_BANKER_SCENARIOS[0])
        assert st.banker.find_safe_sequence() is not None
        assert st.banker.get_available() == [3, 3, 2]
        assert st.last_outcome is None

    def test_granted_request_changes_allocation(self):
        st = BankerStepper(BUILTIN_BANKER_SCENARIOS[0])
        st.forward()
        assert st.last_outcome.granted
        assert st.banker.get_allocation(1) == [3, 0, 2]
        assert st.banker.get_available() == [2, 3, 0]

    def test_denied_request_leaves_state_unchanged(self):
        st = BankerStepper(BUILTIN_BANKER_SCENARIOS[0])
        st.forward()
        before = (st.banker.get_available(), st.banker.get_allocation(0))
        st.forward()  # insufficient
        st.forward()  # unsafe
        assert (st.banker.get_available(), st.banker.get_allocation(0)) == before

    def test_back_undoes_grant(self):
        st = BankerStepper(BUILTIN_BANKER_SCENARIOS[0])
        st.forward()
        st.back()
        assert st.banker.get_available() == [3, 3, 2]
        assert st.outcomes == []
        assert not st.back()

    def test_scenario_not_mutated_by_stepping(self):
        sc = BUILTIN_BANKER_SCENARIOS[0]
        before = {k: list(v) for k, v in sc.allocation.items()}
        st = BankerStepper(sc)
        while st.forward():
            pass
        assert sc.allocation == before


# ===========================================================================
# Yerleşim
# ===========================================================================

class TestLayout:
    def test_all_nodes_placed_on_circle(self):
        pos = circular_layout([1, 2, 3], [1, 2], 500, 400, 200)
        assert set(pos) == {("P", 1), ("P", 2), ("P", 3), ("R", 1), ("R", 2)}
        for x, y in pos.values():
            assert abs(((x - 500) ** 2 + (y - 400) ** 2) ** 0.5 - 200) <= 1

    def test_first_node_at_top(self):
        pos = circular_layout([1], [1], 100, 100, 50)
        assert pos[("P", 1)] == (100, 50)

    def test_positions_unique(self):
        pos = circular_layout(list(range(6)), list(range(6)), 0, 0, 300)
        assert len(set(pos.values())) == 12

    def test_dining_order_follows_cycle(self):
        order = scenario_node_order(_scenario("Dining"))
        assert order == [
            ("P", 1), ("R", 2), ("P", 2), ("R", 3),
            ("P", 3), ("R", 4), ("P", 4), ("R", 1),
        ]

    def test_order_includes_isolated_nodes(self):
        sc = RAGScenario("t", [ProcessSpec(1, "A"), ProcessSpec(2, "B")], [ResourceSpec(9, "Z")])
        assert set(scenario_node_order(sc)) == {("P", 1), ("P", 2), ("R", 9)}

    def test_cycle_nodes_are_adjacent_on_circle(self):
        # Döngüdeki ardışık düğümler çember üzerinde komşu olmalı → çapraz kenar yok
        sc = _scenario("Dining")
        order = scenario_node_order(sc)
        idx = {k: i for i, k in enumerate(order)}
        n = len(order)
        for pid in range(1, 5):
            right = pid % 4 + 1
            assert (idx[("R", right)] - idx[("P", pid)]) % n == 1


# ===========================================================================
# JSON
# ===========================================================================

class TestJSON:
    def test_rag_roundtrip(self, tmp_path):
        sc = _scenario("Dining")
        path = tmp_path / "rag.json"
        save_rag_scenario(sc, path)
        assert load_deadlock_scenario(path) == sc

    def test_banker_roundtrip_restores_int_keys(self, tmp_path):
        sc = BUILTIN_BANKER_SCENARIOS[0]
        path = tmp_path / "banker.json"
        save_banker_scenario(sc, path)
        loaded = load_deadlock_scenario(path)
        assert isinstance(loaded, BankerScenario)
        assert loaded == sc
        assert all(isinstance(k, int) for k in loaded.allocation)

    def test_unknown_type_rejected(self, tmp_path):
        path = tmp_path / "x.json"
        path.write_text('{"type": "nope"}', encoding="utf-8")
        with pytest.raises(ValueError, match="Bilinmeyen senaryo tipi"):
            load_deadlock_scenario(path)

    @pytest.mark.parametrize("name", ["deadlock_rag_demo.json", "deadlock_banker_demo.json"])
    def test_example_files_load_and_replay(self, name):
        sc = load_deadlock_scenario(EXAMPLES / name)
        st = RAGStepper(sc) if isinstance(sc, RAGScenario) else BankerStepper(sc)
        while st.forward():
            pass
        assert st.at_end

    def test_rag_example_reaches_deadlock(self):
        sc = load_deadlock_scenario(EXAMPLES / "deadlock_rag_demo.json")
        st = RAGStepper(sc)
        seen = False
        while st.forward():
            seen = seen or bool(st.deadlocked)
        assert seen


# ===========================================================================
# Headless render
# ===========================================================================

pygame = pytest.importorskip("pygame")


@pytest.fixture
def viz():
    pygame.init()
    from visualization.deadlock_view import DeadlockVisualizer
    yield DeadlockVisualizer()
    pygame.quit()


def _count_color(surface, color, tol=8):
    w, h = surface.get_size()
    hits = 0
    for x in range(0, w, 4):
        for y in range(0, h, 4):
            c = surface.get_at((x, y))
            if all(abs(c[i] - color[i]) <= tol for i in range(3)):
                hits += 1
    return hits


class TestRender:
    def test_deadlock_drawn_in_red(self, viz):
        from visualization.deadlock_view import _DEAD
        surf = pygame.Surface((1024, 768))
        viz.render(surf)
        baseline = _count_color(surf, _DEAD)  # yalnızca lejanttaki nokta
        for _ in range(8):
            viz.handle_key(pygame.K_RIGHT)
        viz.render(surf)
        assert _count_color(surf, _DEAD) > baseline + 50

    def test_recovery_removes_red(self, viz):
        from visualization.deadlock_view import _DEAD
        surf = pygame.Surface((1024, 768))
        viz.render(surf)
        baseline = _count_color(surf, _DEAD)
        while viz.rag.forward():
            pass
        viz.render(surf)
        assert _count_color(surf, _DEAD) == baseline

    def test_banker_mode_renders(self, viz):
        surf = pygame.Surface((1024, 768))
        viz.handle_key(pygame.K_2)
        assert viz.mode == "banker"
        for _ in range(5):
            viz.handle_key(pygame.K_SPACE)
        viz.render(surf)
        assert viz.banker.at_end

    def test_keys(self, viz):
        viz.handle_key(pygame.K_RIGHT)
        viz.handle_key(pygame.K_RIGHT)
        viz.handle_key(pygame.K_LEFT)
        assert viz.rag.step == 1
        viz.handle_key(pygame.K_r)
        assert viz.rag.step == 0
        viz.handle_key(pygame.K_TAB)
        assert viz.rag_index == 1
        assert viz.handle_key(pygame.K_ESCAPE) is False

    def test_scenario_cycle_wraps(self, viz):
        for _ in range(len(viz.rag_scenarios)):
            viz.next_scenario()
        assert viz.rag_index == 0

    def test_autoplay_advances_and_stops_at_end(self, viz):
        viz.handle_key(pygame.K_a)
        assert viz.autoplay
        viz.update(1199)
        assert viz.rag.step == 0
        viz.update(1)
        assert viz.rag.step == 1
        for _ in range(viz.rag.total_steps + 2):
            viz.update(1200)
        assert viz.rag.at_end
        assert not viz.autoplay

    def test_every_builtin_renders_every_step(self, viz):
        surf = pygame.Surface((1024, 768))
        for mode, count in (("rag", len(viz.rag_scenarios)), ("banker", len(viz.banker_scenarios))):
            viz.mode = mode
            for _ in range(count):
                viz.render(surf)
                while viz.stepper.forward():
                    viz.render(surf)
                viz.next_scenario()
