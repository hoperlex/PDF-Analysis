"""The parts coverage of a split sheet (`CMP-SERIES-01`; the original's ``_parts_phase``, ``jobs.py:875-926``)."""

from __future__ import annotations

from auditmanager.comparison.series.parts import PartFact, areas_overlap, group_coverage


def part(rect: list[float] | None, share: float | None, reliable: bool = True) -> PartFact:
    return PartFact(rect, share, reliable)


def test_disjoint_reliable_parts_add_up() -> None:
    percent, reliable = group_coverage(90.0, [part([0, 0, 100, 100], 0.5), part([100, 0, 200, 100], 0.49)])
    assert (percent, reliable) == (99.0, True)


def test_the_sum_is_capped_at_a_hundred_and_at_the_text_coverage_when_the_areas_overlap() -> None:
    assert group_coverage(100.0, [part([0, 0, 100, 100], 0.7), part([200, 0, 300, 100], 0.7)]) == (100.0, True)
    overlapping = [part([0, 0, 100, 100], 0.7), part([20, 0, 120, 100], 0.7)]
    assert group_coverage(80.0, overlapping) == (80.0, True)  # 140 % counted twice, the text figure caps it


def test_an_unreliable_part_gives_the_text_coverage_marked_unreliable() -> None:
    assert group_coverage(77.5, [part([0, 0, 1, 1], 0.9, reliable=False), part([1, 0, 2, 1], 0.1)]) == (77.5, False)
    assert group_coverage(77.5, [part(None, None), part([1, 0, 2, 1], 0.1)]) == (77.5, False)
    assert group_coverage(77.5, []) == (77.5, False)


def test_the_figure_is_a_percentage_in_range() -> None:
    assert group_coverage(250.0, []) == (100.0, False)
    assert group_coverage(-3.0, []) == (0.0, False)
    assert group_coverage(0.0, [part([0, 0, 1, 1], 1.5)])[0] == 100.0


def test_a_hair_of_padding_at_the_cut_is_not_an_overlap() -> None:
    assert not areas_overlap([0, 0, 100, 100], [99, 0, 200, 100])
    assert areas_overlap([0, 0, 100, 100], [50, 0, 200, 100])
