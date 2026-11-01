/**
 * CluesPanel — where clues are written (clue-authoring spec 0.1.4, sections 5.2-5.5).
 *
 * Implements Decision 3 (clue-authoring spec 0.1.4, section 1): clues are written in a Clues panel,
 * one row per entry, with the text committed on blur, Enter or unmount.
 *
 * Implements Decision 2 (clue-authoring spec 0.1.4, section 1): stale and orphaned clues are shown,
 * never silently lost. A stale row offers `Keep`; an orphaned clue sits in its own section with
 * `Delete`.
 *
 * Presentational: every write goes out through a callback and the status shown is the
 * `displayStatuses` prop (R4, section 5.6). The panel never computes a status itself. Each row owns
 * its draft; the committed text arrives through `clues`.
 *
 * Props: grid, clues, displayStatuses, selectedCell ({row, col, direction} | null),
 * editingPaused, onCommit(key, draft) -> {error}, onKeep(key), onDelete(key),
 * onSelect(row, col, dir).
 */
import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { allSlots, slotAt } from '../hooks/useGridGeometry';
import { clueKey, compareClueKeys } from '../lib/clues';

const DOT = '·';
const DASH = '–';

const show = (pattern) => pattern.replace(/\?/g, DOT);

function Boxes({ pattern }) {
  return (
    <div className="xw-clue-pat">
      {Array.from(show(pattern)).map((ch, i) => (
        <span key={i} className={`xw-clue-pat-box${ch === DOT ? ' empty' : ''}`}>
          {ch}
        </span>
      ))}
    </div>
  );
}

function ClueRow({
  entry,
  index,
  committed,
  stale,
  selected,
  editingPaused,
  rowRef,
  inputRef,
  onCommit,
  onKeep,
  onSelect,
  focusRow,
}) {
  const { key, row, col, dir, slot } = entry;
  const [draft, setDraft] = useState(committed);
  const [seen, setSeen] = useState(committed);
  const [error, setError] = useState(null);
  // The draft not yet committed, or null. Cleared the moment a commit is attempted, so a blur that
  // fires while the row unmounts finds nothing left to commit (exactly one commit).
  const pending = useRef(null);
  const latest = useRef({});
  latest.current = { onCommit, key };
  const skipFocusSelect = useRef(false);

  // The committed text changed beneath the draft: the new committed text replaces it.
  if (committed !== seen) {
    setSeen(committed);
    setDraft(committed);
    setError(null);
    pending.current = null;
  }

  const commit = () => {
    if (pending.current === null) return true;
    const value = pending.current;
    pending.current = null;
    const res = latest.current.onCommit(latest.current.key, value);
    if (res && res.error) {
      pending.current = value;
      setError(res.error);
      return false;
    }
    setError(null);
    return true;
  };
  const commitRef = useRef(commit);
  commitRef.current = commit;

  useEffect(() => () => commitRef.current(), []);

  const select = () => onSelect(row, col, dir);
  const label = `Clue for ${slot.number != null ? slot.number : DASH} ${dir}`;

  return (
    <div className={`xw-clue-row${selected ? ' on' : ''}`} ref={rowRef}>
      <button
        type="button"
        className="xw-clue-num"
        onClick={() => {
          select();
          if (!editingPaused && inputRef.current) {
            skipFocusSelect.current = true;
            inputRef.current.focus();
            skipFocusSelect.current = false;
          }
        }}
      >
        {slot.number != null ? slot.number : DASH}
      </button>
      <div className="xw-clue-body">
        <Boxes pattern={slot.pattern} />
        <input
          ref={inputRef}
          className="xw-clue-input"
          type="text"
          placeholder="Write a clue…"
          aria-label={label}
          value={draft}
          disabled={editingPaused}
          onFocus={() => {
            if (!skipFocusSelect.current) select();
          }}
          onChange={(e) => {
            setDraft(e.target.value);
            pending.current = e.target.value;
            setError(null);
          }}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              if (commit()) focusRow(index + 1);
            } else if (e.key === 'Escape') {
              e.preventDefault();
              pending.current = null;
              setDraft(committed);
              setError(null);
            }
          }}
        />
        {error && (
          <div className="xw-clue-empty" role="alert">
            {error}
          </div>
        )}
        {stale && (
          <div className="xw-clue-empty">{`Written for ${show(stale.answer)}`}</div>
        )}
      </div>
      {stale && (
        <button
          type="button"
          className="xw-link-btn"
          disabled={editingPaused}
          onClick={() => onKeep(key)}
        >
          Keep
        </button>
      )}
    </div>
  );
}

export default function CluesPanel({
  grid,
  clues,
  displayStatuses,
  selectedCell,
  editingPaused,
  onCommit,
  onKeep,
  onDelete,
  onSelect,
}) {
  const slots = useMemo(() => allSlots(grid), [grid]);
  const entries = useMemo(() => {
    const mk = (dir) =>
      slots[dir].map((slot) => {
        const [row, col] = slot.cells[0];
        return { key: clueKey(row, col, dir), row, col, dir, slot };
      });
    return { across: mk('across'), down: mk('down') };
  }, [slots]);
  const flat = useMemo(() => [...entries.across, ...entries.down], [entries]);

  const statusOf = (key) => displayStatuses[key];
  const clueKeys = Object.keys(clues);
  const staleCount = clueKeys.filter((k) => statusOf(k) === 'stale').length;
  const orphanKeys = clueKeys.filter((k) => statusOf(k) === 'orphaned').sort(compareClueKeys);

  let sub = `${entries.across.length} across ${DOT} ${entries.down.length} down`;
  if (staleCount > 0) sub += ` ${DOT} ${staleCount} stale`;
  if (orphanKeys.length > 0) sub += ` ${DOT} ${orphanKeys.length} orphaned`;

  const rowEls = useRef({});
  const inputEls = useRef({});

  let selectedKey = null;
  if (selectedCell) {
    const s = slotAt(grid, selectedCell.row, selectedCell.col, selectedCell.direction);
    if (s.length >= 2) {
      selectedKey = clueKey(s.cells[0][0], s.cells[0][1], selectedCell.direction);
    }
  }

  const sRow = selectedCell ? selectedCell.row : null;
  const sCol = selectedCell ? selectedCell.col : null;
  const sDir = selectedCell ? selectedCell.direction : null;
  useLayoutEffect(() => {
    if (selectedKey === null) return;
    const el = rowEls.current[selectedKey];
    if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
  }, [selectedKey, sRow, sCol, sDir]);

  const focusRow = (i) => {
    const next = flat[i];
    const el = next && inputEls.current[next.key] && inputEls.current[next.key].current;
    if (el) el.focus();
  };

  const renderRow = (entry) => {
    const index = flat.indexOf(entry);
    if (!inputEls.current[entry.key]) inputEls.current[entry.key] = { current: null };
    const inputRef = inputEls.current[entry.key];
    const status = statusOf(entry.key);
    const clue = clues[entry.key];
    return (
      <ClueRow
        key={entry.key}
        entry={entry}
        index={index}
        committed={clue ? clue.text : ''}
        stale={clue && status === 'stale' ? clue : null}
        selected={entry.key === selectedKey}
        editingPaused={editingPaused}
        rowRef={(el) => {
          rowEls.current[entry.key] = el;
        }}
        inputRef={inputRef}
        onCommit={onCommit}
        onKeep={onKeep}
        onSelect={onSelect}
        focusRow={focusRow}
      />
    );
  };

  const group = (title, dir, empty) => (
    <div className="xw-clue-group">
      <div className="xw-clue-head">
        {title} <em>{`${DOT} ${entries[dir].length}`}</em>
      </div>
      <div className="xw-clue-list">
        {entries[dir].length === 0 ? (
          <div className="xw-clue-empty">{empty}</div>
        ) : (
          entries[dir].map(renderRow)
        )}
      </div>
    </div>
  );

  return (
    <div className="xw-clues">
      <div className="xw-clues-head-bar">
        <strong>Clues</strong>
        <em>{sub}</em>
      </div>
      {group('Across', 'across', 'No across words yet.')}
      {group('Down', 'down', 'No down words yet.')}
      {orphanKeys.length > 0 && (
        <div className="xw-clue-group">
          <div className="xw-clue-head">
            Orphaned <em>{`${DOT} ${orphanKeys.length}`}</em>
          </div>
          <div className="xw-clue-empty">
            These entries no longer exist. Copy a clue into an entry, or delete it.
          </div>
          <div className="xw-clue-list">
            {orphanKeys.map((key) => (
              <div className="xw-clue-row" key={key}>
                <div className="xw-clue-body">
                  <Boxes pattern={clues[key].answer} />
                  <span>{clues[key].text}</span>
                </div>
                <button
                  type="button"
                  className="xw-danger-btn"
                  disabled={editingPaused}
                  onClick={() => onDelete(key)}
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
