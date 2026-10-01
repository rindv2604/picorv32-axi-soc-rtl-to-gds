"""LibreLane 3.0.1 full RTL-to-GDS flow for deterministic ECO19 replay."""

from pathlib import Path

from librelane.flows import Flow
from librelane.flows.builtins import Classic
from librelane.steps import OpenROAD, Step


_TOP = Path(__file__).resolve().parent.parent
_SCRIPTS = _TOP / "scripts" / "eco19_repro"


@Step.factory.register()
class ApplyFinalSlewFix(OpenROAD.DetailedRouting):
    """Replay, legal-check, incrementally route, and verify accepted ECO19."""

    id = "ECO19.ApplyFinalSlewFix"
    name = "Apply Final ECO19 Slew Fix"

    def get_script_path(self) -> str:
        return str(_SCRIPTS / "eco19_step.tcl")


@Step.factory.register()
class FinalRefill(OpenROAD.FillInsertion):
    """Use the exact four-master filler policy accepted for ECO19."""

    id = "ECO19.FinalRefill"
    name = "ECO19 Final Refill"

    def get_script_path(self) -> str:
        return str(_SCRIPTS / "refill_eco19.tcl")


@Flow.factory.register()
class ECO19FullRepro(Classic):
    """Classic plus post-DRT accepted ECO19 replay and deterministic refill."""

    name = "ECO19 Full RTL-to-GDS Reproduction"
    Substitutions = [
        ("+OpenROAD.DetailedRouting", ApplyFinalSlewFix),
        ("OpenROAD.FillInsertion", FinalRefill),
    ]
