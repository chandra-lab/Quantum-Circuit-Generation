"""Render the Qiskit circuit that was actually built."""

from __future__ import annotations

import io
import logging

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.core.errors import SimulationError

logger = logging.getLogger(__name__)


def circuit_to_svg(circuit: object) -> str:
    figure = None
    try:
        figure = circuit.draw(output="mpl", fold=-1, idle_wires=True)  # type: ignore[attr-defined]
        buffer = io.StringIO()
        figure.savefig(buffer, format="svg", bbox_inches="tight")
        svg = buffer.getvalue()
    except Exception as exc:
        logger.warning("circuit svg render failed: %s", type(exc).__name__)
        raise SimulationError("The circuit diagram could not be rendered.") from exc
    finally:
        if figure is not None:
            plt.close(figure)
    start = svg.find("<svg")
    if start < 0:
        raise SimulationError("The circuit diagram could not be rendered.")
    return svg[start:]
