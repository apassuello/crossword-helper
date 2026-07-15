// AutofillPanel — Constructor's Bench autofill panel (Task 11B).
// Ported from the design bundle prototype (panels.jsx:359-462) — LAYOUT ONLY.
// The bundle's algorithm list (back/random), preferPersonal checkbox, preset
// cards, and progress-ticker are fiction; real fields/behavior come from the
// OLD `src/components/AutofillPanel.jsx` (getThemeEntries logic verbatim,
// options shape) minus everything pause/resume/black-square-modal related.
//
// Presentational / fully controlled for lifecycle: this component owns only
// the options FORM state + the one-time wordlist fetch on mount. All
// start/cancel/reset/progress state comes from `machine`, shaped exactly like
// `useAutofillMachine()`'s return value (Task 11A, binding contract):
//   { state, taskId, progress, message, errorCard, start, cancel, reset }
// `state` is one of idle|submitting|running|done|failed|cancelled|paused.
// This component never touches SSE/EventSource/the API client directly,
// except for `api.getWordlists()` (read-only, display purposes).
//
// Dropped vs. the old panel (see task-11B-brief.md "What to DROP"):
//   - preferPersonalWords: removed entirely, not just hidden — the endpoint
//     rejects it (B5 deferred), so the field doesn't exist in options state.
//   - themeList (custom-wordlist-as-theme radio designation): also dropped.
//     Not in the brief's port list, and useAutofillMachine's start() has a
//     fixed whitelist of fields forwarded to api.startFill() that does NOT
//     include it (only `themeEntries`, derived from grid theme-locked cells,
//     is forwarded) — keeping a themeList control would render a dead UI
//     element indistinguishable in kind from preferPersonalWords.
//   - All pause/resume UI (state, handlers, resume-prompt banner, the
//     mount-time localStorage read) and the black-square suggestion modal —
//     pause lands in F11, black squares in Task 20. The "Suggest Black
//     Square" button itself stays, permanently disabled.
//   - ProgressIndicator: never imported. Global constraint — no spinners.
//     Progress is always a bar (`.xw-progress-bar`/`.xw-progress-fill`).
//
// Option defaults are passed EXPLICITLY on every start() call (never omitted)
// per the 11A review finding: the hook doesn't default options itself, and
// omitting minScore would let the backend's default (30) silently override
// this panel's user-visible default (50, matching the old panel).

import React, { useEffect, useState } from 'react';
import { api } from '../../api/client';
import { allSlots } from '../../hooks/useGridGeometry';

const DEFAULT_OPTIONS = {
  algorithm: 'repair',
  timeout: 300,
  minScore: 50,
  adaptiveMode: false,
  maxAdaptations: 3,
  partialFill: false,
  cleanup: false,
  wordlists: ['comprehensive'],
};

/** Count slots (across + down, length >= 2) that still have at least one empty cell. */
function countEmptySlots(grid) {
  if (!grid) return 0;
  const { across, down } = allSlots(grid);
  return across.concat(down).filter((slot) => slot.pattern.includes('?')).length;
}

/**
 * Ported verbatim from the old panel (`src/components/AutofillPanel.jsx:224-319`):
 * find contiguous theme-locked runs (across + down) and key them
 * `(row,col,direction)` -> word, exactly as the CLI's `--theme-entries`
 * flag expects. Length-1 runs are excluded (not real entries).
 */
function getThemeEntries(grid) {
  if (!grid) return {};

  const themeEntries = {};
  const visited = new Set();

  const extractThemeWord = (startRow, startCol, direction) => {
    let word = '';
    if (direction === 'across') {
      let c = startCol;
      while (
        c < grid[startRow].length &&
        !grid[startRow][c].isBlack &&
        grid[startRow][c].isThemeLocked &&
        grid[startRow][c].letter
      ) {
        word += grid[startRow][c].letter;
        visited.add(`${startRow},${c},across`);
        c++;
      }
    } else {
      let r = startRow;
      while (
        r < grid.length &&
        !grid[r][startCol].isBlack &&
        grid[r][startCol].isThemeLocked &&
        grid[r][startCol].letter
      ) {
        word += grid[r][startCol].letter;
        visited.add(`${r},${startCol},down`);
        r++;
      }
    }
    return word;
  };

  for (let row = 0; row < grid.length; row++) {
    for (let col = 0; col < grid[row].length; col++) {
      const cell = grid[row][col];
      if (cell.isThemeLocked && !cell.isBlack && cell.letter) {
        const cellKey = `${row},${col},across`;
        if (!visited.has(cellKey)) {
          const isThemeStart = col === 0 || !grid[row][col - 1].isThemeLocked || grid[row][col - 1].isBlack;
          if (isThemeStart) {
            const word = extractThemeWord(row, col, 'across');
            if (word.length > 1) themeEntries[`(${row},${col},across)`] = word;
          }
        }
      }
    }
  }

  for (let col = 0; col < grid[0].length; col++) {
    for (let row = 0; row < grid.length; row++) {
      const cell = grid[row][col];
      if (cell.isThemeLocked && !cell.isBlack && cell.letter) {
        const cellKey = `${row},${col},down`;
        if (!visited.has(cellKey)) {
          const isThemeStart = row === 0 || !grid[row - 1][col].isThemeLocked || grid[row - 1][col].isBlack;
          if (isThemeStart) {
            const word = extractThemeWord(row, col, 'down');
            if (word.length > 1) themeEntries[`(${row},${col},down)`] = word;
          }
        }
      }
    }
  }

  return themeEntries;
}

function SuggestBlackSquareButton() {
  return (
    <button className="xw-ghost-btn" disabled title="lands in Task 20">
      Suggest Black Square
    </button>
  );
}

export function AutofillPanel({ machine, grid }) {
  const [options, setOptions] = useState(DEFAULT_OPTIONS);
  const [availableWordlists, setAvailableWordlists] = useState({ built_in: [], custom: [] });
  const [wordlistsLoading, setWordlistsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.getWordlists().then(
      (res) => {
        if (cancelled) return;
        const lists = (res && res.wordlists) || [];
        setAvailableWordlists({
          built_in: lists.filter((wl) => wl.category !== 'custom'),
          custom: lists.filter((wl) => wl.category === 'custom'),
        });
        setWordlistsLoading(false);
      },
      () => {
        if (cancelled) return;
        setWordlistsLoading(false);
      }
    );
    return () => {
      cancelled = true;
    };
  }, []);

  const handleOptionChange = (key, value) => setOptions((prev) => ({ ...prev, [key]: value }));

  const toggleWordlist = (id, checked) => {
    const lists = checked ? [...options.wordlists, id] : options.wordlists.filter((l) => l !== id);
    handleOptionChange('wordlists', lists);
  };

  const emptySlots = countEmptySlots(grid);
  const themeCount = Object.keys(getThemeEntries(grid)).length;

  const handleStart = () => {
    machine.start({ ...options, themeEntries: getThemeEntries(grid) });
  };

  const { state } = machine;
  const inProgress = state === 'submitting' || state === 'running';
  const isTerminal = state === 'done' || state === 'failed' || state === 'cancelled';

  return (
    <div className="xw-autofill">
      <div className="xw-af-head">
        <h3>
          Autofill
          <em>
            {' '}
            · {emptySlots} empty slots{themeCount > 0 ? `, ${themeCount} theme words` : ''}
          </em>
        </h3>
      </div>

      {state === 'paused' && (
        <div className="xw-af-progress-panel">
          <div className="xw-af-progress-label">paused — resume support lands with F11</div>
          <div className="xw-af-actions-row">
            <button className="xw-ghost-btn" onClick={machine.reset}>
              Reset
            </button>
          </div>
        </div>
      )}

      {inProgress && (
        <div className="xw-af-progress-panel">
          <div className="xw-af-progress-label">{machine.message}</div>
          <div className="xw-progress-bar">
            <div className="xw-progress-fill" style={{ width: `${machine.progress}%` }} />
          </div>
          <div className="xw-progress-meta">
            <span>{machine.progress}%</span>
          </div>
          {state === 'running' && (
            <div className="xw-af-actions-row">
              <button className="xw-danger-btn" onClick={machine.cancel}>
                Cancel
              </button>
              <SuggestBlackSquareButton />
            </div>
          )}
        </div>
      )}

      {isTerminal && (
        <div className="xw-af-progress-panel">
          <div className="xw-af-done-msg">
            {/* Tone tracks errorCard presence (brief: "color/tone via errorCard
                presence") — failed reads red, done/cancelled read the neutral
                "good" token. Inline style, not a new class: matches the design
                bundle's own approach for the equivalent done-state accent. */}
            <strong style={{ color: state === 'failed' ? 'var(--danger)' : 'var(--good)' }}>
              {state === 'failed' ? machine.errorCard && machine.errorCard.message : machine.message}
            </strong>
          </div>
          <div className="xw-af-actions-row">
            <button className="xw-ghost-btn" onClick={machine.reset}>
              Reset
            </button>
          </div>
        </div>
      )}

      <div className="xw-af-opts">
        <div className="xw-af-section-head">Options</div>
        <div className="xw-form-grid">
          <label className="xw-form-row">
            <span>Algorithm</span>
            <select value={options.algorithm} onChange={(e) => handleOptionChange('algorithm', e.target.value)}>
              <option value="repair">Repair (Recommended)</option>
              <option value="hybrid">Hybrid (Beam + Repair)</option>
              <option value="beam">Beam Search</option>
              <option value="trie">Classic CSP</option>
            </select>
          </label>
          <label className="xw-form-row">
            <span>Timeout</span>
            <select
              value={options.timeout}
              onChange={(e) => handleOptionChange('timeout', parseInt(e.target.value, 10))}
            >
              <option value="60">1 min</option>
              <option value="120">2 min</option>
              <option value="300">5 min</option>
              <option value="600">10 min</option>
              <option value="1800">30 min</option>
            </select>
          </label>
          <label className="xw-form-row">
            <span>
              Min Score: <b>{options.minScore}</b>
            </span>
            <input
              type="range"
              min="0"
              max="100"
              step="10"
              value={options.minScore}
              onChange={(e) => handleOptionChange('minScore', parseInt(e.target.value, 10))}
            />
          </label>
        </div>

        <div className="xw-af-checkgrid">
          <label className="xw-check">
            <input
              type="checkbox"
              checked={options.adaptiveMode}
              onChange={(e) => handleOptionChange('adaptiveMode', e.target.checked)}
            />
            <span>Adaptive mode</span>
          </label>
          <label className="xw-check">
            <input
              type="checkbox"
              checked={options.partialFill}
              onChange={(e) => handleOptionChange('partialFill', e.target.checked)}
            />
            <span>Partial fill</span>
          </label>
          <label className="xw-check">
            <input
              type="checkbox"
              checked={options.cleanup}
              onChange={(e) => handleOptionChange('cleanup', e.target.checked)}
            />
            <span>Cleanup invalid words</span>
          </label>
        </div>

        {options.adaptiveMode && (
          <div className="xw-form-grid xw-form-grid-condit">
            <label className="xw-form-row">
              <span>
                Max adaptations: <b>{options.maxAdaptations}</b>
              </span>
              <input
                type="range"
                min="1"
                max="5"
                step="1"
                value={options.maxAdaptations}
                onChange={(e) => handleOptionChange('maxAdaptations', parseInt(e.target.value, 10))}
              />
            </label>
          </div>
        )}

        <div className="xw-af-section-head">Word Lists</div>
        {wordlistsLoading ? (
          <div>Loading…</div>
        ) : (
          <>
            {availableWordlists.built_in.length > 0 && (
              <>
                <div className="xw-af-section-head">Built-in</div>
                <div className="xw-af-checkgrid">
                  {availableWordlists.built_in.map((wl) => {
                    const id = wl.key || wl.name;
                    return (
                      <label className="xw-check" key={id}>
                        <input
                          type="checkbox"
                          checked={options.wordlists.includes(id)}
                          onChange={(e) => toggleWordlist(id, e.target.checked)}
                        />
                        <span>
                          {wl.name}
                          {wl.word_count ? ` (${wl.word_count.toLocaleString()})` : ''}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </>
            )}
            {availableWordlists.custom.length > 0 && (
              <>
                <div className="xw-af-section-head">Custom</div>
                <div className="xw-af-checkgrid">
                  {availableWordlists.custom.map((wl) => {
                    const id = wl.key || wl.name;
                    return (
                      <label className="xw-check" key={id}>
                        <input
                          type="checkbox"
                          checked={options.wordlists.includes(id)}
                          onChange={(e) => toggleWordlist(id, e.target.checked)}
                        />
                        <span>
                          {wl.name}
                          {wl.word_count ? ` (${wl.word_count.toLocaleString()})` : ''}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </>
            )}
          </>
        )}
      </div>

      {state === 'idle' && (
        <div className="xw-af-footer">
          <button className="xw-primary-btn" onClick={handleStart} disabled={emptySlots === 0}>
            Start Autofill
          </button>
          {emptySlots > 0 && <SuggestBlackSquareButton />}
        </div>
      )}
    </div>
  );
}

export default AutofillPanel;
