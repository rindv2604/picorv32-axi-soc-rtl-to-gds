import collections
import json
import os

import odb


def load(path):
    db = odb.dbDatabase.create()
    odb.read_db(db, path)
    return db, db.getChip().getBlock()


_, baseline = load(os.environ["ECO4O_BASELINE_ODB"])
_, final = load(os.environ["ECO4O_FINAL_ODB"])
baseline_insts = {inst.getName(): inst for inst in baseline.getInsts()}
final_insts = {inst.getName(): inst for inst in final.getInsts()}

inserted_names = sorted(set(final_insts) - set(baseline_insts))
logical_inserted = [
    name for name in inserted_names if not name.startswith("eco4o_fill_")
]
physical_fillers = [name for name in inserted_names if name.startswith("eco4o_fill_")]
removed_names = sorted(set(baseline_insts) - set(final_insts))
modified_names = []
for name in sorted(set(baseline_insts) & set(final_insts)):
    old = baseline_insts[name]
    new = final_insts[name]
    if (
        old.getMaster().getName() != new.getMaster().getName()
        or old.getLocation() != new.getLocation()
        or str(old.getOrient()) != str(new.getOrient())
    ):
        modified_names.append(name)


def master_counts(names, instances):
    return dict(
        sorted(
            collections.Counter(
                instances[name].getMaster().getName() for name in names
            ).items()
        )
    )


report = {
    "frozen_revision": "top_newcpu_eco4o_19",
    "logical_inserted_count": len(logical_inserted),
    "logical_inserted_master_counts": master_counts(logical_inserted, final_insts),
    "logical_inserted_instances": logical_inserted,
    "physical_filler_count": len(physical_fillers),
    "physical_filler_master_counts": master_counts(physical_fillers, final_insts),
    "modified_original_count": len(modified_names),
    "modified_original_instances": modified_names,
    "removed_original_count": len(removed_names),
    "removed_original_master_counts": master_counts(removed_names, baseline_insts),
    "removed_original_instances": removed_names,
}
with open(os.environ["ECO4O_DELTA_REPORT"], "w") as stream:
    json.dump(report, stream, indent=2)
print(json.dumps({key: value for key, value in report.items() if not key.endswith("instances")}, indent=2))
