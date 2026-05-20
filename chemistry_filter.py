#!/usr/bin/env python3
"""
化学论文过滤模块
提供化学相关性检查函数与默认检索关键词。
"""

from typing import Iterable, Optional
import re


DEFAULT_CHEMISTRY_KEYWORDS = [
    "chemistry",
    "chemical synthesis",
    "organic synthesis",
    "catalysis",
    "electrochemistry",
    "computational chemistry",
    "materials chemistry",
    "chemical biology",
]

STRONG_CHEMISTRY_PATTERNS = [
    "chemical synthesis",
    "organic synthesis",
    "asymmetric synthesis",
    "total synthesis",
    "catalysis",
    "catalytic",
    "electrocatalysis",
    "electrochemistry",
    "electrochemical",
    "computational chemistry",
    "materials chemistry",
    "chemical biology",
    "reaction mechanism",
    "molecular design",
    "ligand design",
    "polymer chemistry",
    "spectroscopy",
    "spectrometric",
    "mass spectrometry",
    "nmr",
    "ftir",
    "xrd",
    "xps",
]

CHEMISTRY_TERMS = [
    "chemistry",
    "chemical",
    "molecule",
    "molecular",
    "compound",
    "reaction",
    "synthesis",
    "synthesized",
    "catalyst",
    "catalytic",
    "electrode",
    "electrochemical",
    "polymer",
    "ligand",
    "enzyme",
    "substrate",
    "reagent",
    "selectivity",
    "yield",
    "stereoselectivity",
    "chirality",
    "material",
    "organic",
    "inorganic",
    "analytical",
    "biochemical",
    "pharmaceutical",
]

CHEMISTRY_CONTEXT_TERMS = [
    "mechanism",
    "characterization",
    "structure",
    "kinetics",
    "thermodynamics",
    "pathway",
    "selective",
    "spectrum",
    "spectra",
    "battery",
    "electrolyte",
    "nanomaterial",
    "coordination",
    "metallation",
    "polymerization",
    "biocatalysis",
    "assay",
    "crystal",
]


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    return any(term.lower() in text for term in terms)


def is_chemistry_related(title: str, abstract: str, exclude_terms: Optional[Iterable[str]] = None) -> bool:
    """判断论文是否与化学方向相关。"""
    text = f" {title} {abstract} ".lower()

    if exclude_terms and _contains_any(text, exclude_terms):
        return False

    if any(pattern in text for pattern in STRONG_CHEMISTRY_PATTERNS):
        return True

    if re.search(r"\b(?:nmr|ftir|xrd|xps|hplc|gc-ms|lc-ms|dft|md)\b", text):
        return True

    has_chemistry_signal = _contains_any(text, CHEMISTRY_TERMS)
    has_context_signal = _contains_any(text, CHEMISTRY_CONTEXT_TERMS)
    return has_chemistry_signal and has_context_signal

