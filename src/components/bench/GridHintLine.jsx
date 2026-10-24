// novice-readiness spec 0.2.7 §3.3 (G7): the always-visible key hint under the
// grid. It lists the primary keys only; a test asserts that dispatchGridKey
// handles every key it names.

export const GRID_HINT =
  'Type letters · Arrows move · Space or . black square · Enter switch direction · Tab next word · Backspace clear';

export default function GridHintLine() {
  return <p className="xw-grid-hint">{GRID_HINT}</p>;
}
