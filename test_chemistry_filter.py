import pytest

from chemistry_filter import is_chemistry_related


@pytest.mark.parametrize(
    "title, abstract, expected",
    [
        ("Catalytic Enantioselective Synthesis of Complex Molecules", "", True),
        ("Electrochemical CO2 Reduction on Copper Single-Atom Catalysts", "", True),
        ("Computational Chemistry for Reaction Mechanism Discovery", "", True),
        ("", "We report a new ligand design for asymmetric catalysis and structure characterization.", True),
        ("Organic Synthesis of a Heterocycle with High Yield and Selectivity", "", True),
        ("Materials Chemistry for Catalyst Design with Graph Neural Networks", "", True),
        ("Large Language Models for Molecular Design", "", True),
        ("Vision-Language Models for Image Classification", "", False),
        ("Neural Machine Translation with Large Language Models", "", False),
        ("Trajectory Prediction for Autonomous Driving", "", False),
    ],
)
def test_is_chemistry_related(title, abstract, expected):
    assert is_chemistry_related(title, abstract) is expected


def test_exclude_terms_can_block_known_noise():
    title = "Catalytic Synthesis with a Draft Placeholder"
    abstract = "This paper is about chemistry but should be filtered by explicit exclusions."
    assert is_chemistry_related(title, abstract, exclude_terms=["draft placeholder"]) is False
