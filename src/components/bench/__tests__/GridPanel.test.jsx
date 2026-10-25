// novice-readiness spec 0.2.7 §3.3 (G7) / §3.2: the Grid panel's Black square toggle.
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, within, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GridPanel from '../GridPanel';
import storage from '../../../lib/storage';

const SIZE = 5;
const makeGrid = (patch = {}) =>
  Array.from({ length: SIZE }, (_, r) =>
    Array.from({ length: SIZE }, (_, c) => ({
      row: r,
      col: c,
      letter: '',
      isBlack: false,
      isThemeLocked: false,
      ...(patch[`${r},${c}`] || {}),
    }))
  );

const sel = (row, col) => ({ row, col, direction: 'across' });

const setup = (over = {}) => {
  const onToggleBlack = vi.fn();
  const onNewGrid = vi.fn();
  const props = {
    grid: makeGrid(),
    gridSize: SIZE,
    selectedCell: sel(1, 1),
    symmetryEnabled: true,
    editingPaused: false,
    onToggleBlack,
    onNewGrid,
    ...over,
  };
  const { rerender } = render(<GridPanel {...props} />);
  return { rerender, onToggleBlack, onNewGrid, button: screen.getByRole('button', { name: 'Black square' }) };
};

describe('GridPanel Black square (§3.3)', () => {
  it('is disabled with no selected cell', () => {
    const { button } = setup({ selectedCell: null });
    expect(button).toBeDisabled();
  });

  it('is enabled for an unlocked cell and calls onToggleBlack(1, 1) on click', async () => {
    const { button, onToggleBlack } = setup();
    expect(button).toBeEnabled();
    await userEvent.setup().click(button);
    expect(onToggleBlack).toHaveBeenCalledTimes(1);
    expect(onToggleBlack).toHaveBeenCalledWith(1, 1);
  });

  it('acts on the selected cell, not a fixed one', async () => {
    const { button, onToggleBlack } = setup({ selectedCell: sel(0, 2) });
    await userEvent.setup().click(button);
    expect(onToggleBlack).toHaveBeenCalledWith(0, 2);
  });

  it('is disabled when the selected cell is theme-locked', () => {
    const { button } = setup({ grid: makeGrid({ '1,1': { isThemeLocked: true } }) });
    expect(button).toBeDisabled();
  });

  it('is disabled when the mirror (3,3) is theme-locked and symmetry is on', () => {
    const { button } = setup({ grid: makeGrid({ '3,3': { isThemeLocked: true } }) });
    expect(button).toBeDisabled();
  });

  it('is enabled when the mirror is theme-locked but symmetry is off', () => {
    const { button } = setup({
      grid: makeGrid({ '3,3': { isThemeLocked: true } }),
      symmetryEnabled: false,
    });
    expect(button).toBeEnabled();
  });

  it('is disabled while editing is paused', () => {
    const { button } = setup({ editingPaused: true });
    expect(button).toBeDisabled();
  });

  it('carries aria-pressed for whether the selected cell is black', () => {
    const { button } = setup({ grid: makeGrid({ '1,1': { isBlack: true } }) });
    expect(button).toHaveAttribute('aria-pressed', 'true');
  });

  it('aria-pressed is false for a white cell and for no selection', () => {
    const { button } = setup();
    expect(button).toHaveAttribute('aria-pressed', 'false');
  });
});

// novice-readiness spec 0.2.7 §3.2 (#55): New grid with an in-panel confirm.
describe('GridPanel New grid (§3.2)', () => {
  const withContent = () => makeGrid({ '0,0': { letter: 'A' } });
  const sizeBtn = (label) => screen.getByRole('button', { name: label });

  it('offers exactly 11×11, 15×15 and 21×21 (× is U+00D7)', () => {
    setup();
    for (const label of ['11\u00d711', '15\u00d715', '21\u00d721']) {
      expect(sizeBtn(label)).toBeInTheDocument();
    }
  });

  it('on a grid with no letter and no black square, calls onNewGrid(size) with no confirm', async () => {
    const { onNewGrid } = setup();
    await userEvent.setup().click(sizeBtn('11\u00d711'));
    expect(onNewGrid).toHaveBeenCalledTimes(1);
    expect(onNewGrid).toHaveBeenCalledWith(11);
    expect(screen.queryByRole('group')).toBeNull();
  });

  it('on a grid with a letter, shows the confirm and does not call onNewGrid yet', async () => {
    const { onNewGrid } = setup({ grid: withContent() });
    await userEvent.setup().click(sizeBtn('21\u00d721'));
    expect(onNewGrid).not.toHaveBeenCalled();
    expect(screen.getByRole('group')).toHaveTextContent(
      'Replace the current grid? Unsaved changes are lost.'
    );
  });

  it('a black square alone also needs the confirm', async () => {
    const { onNewGrid } = setup({ grid: makeGrid({ '2,2': { isBlack: true } }) });
    await userEvent.setup().click(sizeBtn('15\u00d715'));
    expect(onNewGrid).not.toHaveBeenCalled();
    expect(screen.getByRole('group')).toBeInTheDocument();
  });

  it('Replace calls onNewGrid with the chosen size and closes the confirm', async () => {
    const user = userEvent.setup();
    const { onNewGrid } = setup({ grid: withContent() });
    await user.click(sizeBtn('21\u00d721'));
    await user.click(screen.getByRole('button', { name: 'Replace' }));
    expect(onNewGrid).toHaveBeenCalledTimes(1);
    expect(onNewGrid).toHaveBeenCalledWith(21);
    expect(screen.queryByRole('group')).toBeNull();
  });

  it('Cancel closes the confirm and changes nothing', async () => {
    const user = userEvent.setup();
    const { onNewGrid } = setup({ grid: withContent() });
    await user.click(sizeBtn('15\u00d715'));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onNewGrid).not.toHaveBeenCalled();
    expect(screen.queryByRole('group')).toBeNull();
  });

  it('disables all three size buttons while editing is paused', () => {
    setup({ editingPaused: true });
    for (const label of ['11\u00d711', '15\u00d715', '21\u00d721']) {
      expect(sizeBtn(label)).toBeDisabled();
    }
  });

  it('drops an open confirm when the panel unmounts', async () => {
    const user = userEvent.setup();
    const props = {
      grid: withContent(),
      gridSize: SIZE,
      selectedCell: null,
      symmetryEnabled: true,
      editingPaused: false,
      onToggleBlack: vi.fn(),
      onNewGrid: vi.fn(),
    };
    const { unmount } = render(<GridPanel {...props} />);
    await user.click(sizeBtn('15\u00d715'));
    expect(screen.getByRole('group')).toBeInTheDocument();
    unmount();
    render(<GridPanel {...props} />);
    expect(screen.queryByRole('group')).toBeNull();
  });
});

// novice-readiness spec 0.2.7 §3.4 (PD-6-G20): Open saved, Delete and the single-confirm rule.
describe('GridPanel Open saved (§3.4)', () => {
  const at = (d, h, m) => new Date(2026, 9, d, h, m).toISOString();
  const E1 = { id: 'one', name: 'First', size: 15, savedAt: at(23, 18, 5), grid: [] };
  const E2 = { id: 'two', name: 'Second', size: 11, savedAt: at(22, 9, 30), grid: [] };
  const REPLACE = 'Replace the current grid? Unsaved changes are lost.';
  const filled = () => makeGrid({ '0,0': { letter: 'A' } });

  afterEach(() => vi.restoreAllMocks());

  // novice-readiness spec 0.2.10 §3.4: the token App hands out at the confirm travels back.
  const TOKEN = 7;
  const setupOpen = async (over = {}) => {
    const listed = [E1, E2];
    const listSpy = vi.spyOn(storage, 'list').mockImplementation(() => Promise.resolve([...listed]));
    const removeSpy = vi.spyOn(storage, 'remove').mockImplementation((id) => {
      listed.splice(listed.findIndex((e) => e.id === id), 1);
      return Promise.resolve();
    });
    const onOpenSaved = vi.fn();
    const user = userEvent.setup();
    const utils = setup({ onOpenBegin: () => TOKEN, onOpenSaved, ...over });
    return { ...utils, user, onOpenSaved, listSpy, removeSpy };
  };
  const rowOf = (name) => screen.getByText(name).closest('li');
  const showList = async (user) => {
    // list() resolves after the click; flush it inside act so the state update is wrapped.
    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Open saved' }));
    });
    await screen.findByText('First');
  };

  it('lists nothing until Open saved is pressed, then one row per stored entry, newest first', async () => {
    const { user, listSpy } = await setupOpen();
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
    expect(listSpy).not.toHaveBeenCalled();
    await showList(user);
    const rows = screen.getAllByRole('listitem');
    expect(rows.map((r) => r.textContent)).toEqual([
      expect.stringContaining('First'),
      expect.stringContaining('Second'),
    ]);
  });

  it('Delete asks Delete "<name>"? first; nothing is removed yet', async () => {
    const { user, removeSpy } = await setupOpen();
    await showList(user);
    await user.click(within(rowOf('First')).getByRole('button', { name: 'Delete' }));
    const confirm = screen.getByRole('group', { name: 'Delete "First"?' });
    expect(within(confirm).getByRole('button', { name: 'Delete' })).toBeInTheDocument();
    expect(within(confirm).getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    expect(removeSpy).not.toHaveBeenCalled();
  });

  it('the Delete confirm renders above the list (PD-6-G20)', async () => {
    const { user } = await setupOpen();
    await showList(user);
    await user.click(within(rowOf('First')).getByRole('button', { name: 'Delete' }));
    const confirm = screen.getByRole('group', { name: 'Delete "First"?' });
    const list = screen.getAllByRole('listitem')[0].parentElement;
    expect(confirm.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('confirming Delete removes that id and the row disappears', async () => {
    const { user, removeSpy } = await setupOpen();
    await showList(user);
    await user.click(within(rowOf('First')).getByRole('button', { name: 'Delete' }));
    const confirm = screen.getByRole('group', { name: 'Delete "First"?' });
    await act(async () => {
      await user.click(within(confirm).getByRole('button', { name: 'Delete' }));
    });
    expect(removeSpy).toHaveBeenCalledTimes(1);
    expect(removeSpy).toHaveBeenCalledWith('one');
    await waitFor(() => expect(screen.queryByText('First')).toBeNull());
    expect(screen.getByText('Second')).toBeInTheDocument();
    expect(screen.queryByRole('group')).toBeNull();
  });

  it('cancelling Delete removes nothing and the row stays', async () => {
    const { user, removeSpy } = await setupOpen();
    await showList(user);
    await user.click(within(rowOf('First')).getByRole('button', { name: 'Delete' }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(removeSpy).not.toHaveBeenCalled();
    expect(screen.getByText('First')).toBeInTheDocument();
    expect(screen.queryByRole('group')).toBeNull();
  });

  it('Open on a blank grid opens at once with that entry and no confirm', async () => {
    const { user, onOpenSaved } = await setupOpen();
    await showList(user);
    await user.click(within(rowOf('Second')).getByRole('button', { name: 'Open' }));
    expect(onOpenSaved).toHaveBeenCalledTimes(1);
    expect(onOpenSaved).toHaveBeenCalledWith(E2, TOKEN);
    expect(screen.queryByRole('group')).toBeNull();
  });

  it('Open on a grid with content asks first; Cancel opens nothing, Replace opens that entry', async () => {
    const { user, onOpenSaved } = await setupOpen({ grid: filled() });
    await showList(user);
    await user.click(within(rowOf('Second')).getByRole('button', { name: 'Open' }));
    expect(screen.getByRole('group', { name: REPLACE })).toBeInTheDocument();
    expect(onOpenSaved).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onOpenSaved).not.toHaveBeenCalled();
    expect(screen.queryByRole('group')).toBeNull();

    await user.click(within(rowOf('Second')).getByRole('button', { name: 'Open' }));
    await user.click(screen.getByRole('button', { name: 'Replace' }));
    expect(onOpenSaved).toHaveBeenCalledTimes(1);
    expect(onOpenSaved).toHaveBeenCalledWith(E2, TOKEN);
    expect(screen.queryByRole('group')).toBeNull();
  });

  it('only one confirm is open at a time, whichever opens last', async () => {
    const { user } = await setupOpen({ grid: filled() });
    await showList(user);
    const sizeBtn = screen.getByRole('button', { name: '11\u00d711' });

    await user.click(sizeBtn); // New grid confirm
    expect(screen.getAllByRole('group')).toHaveLength(1);
    await user.click(within(rowOf('First')).getByRole('button', { name: 'Delete' }));
    expect(screen.getAllByRole('group')).toHaveLength(1);
    expect(screen.getByRole('group', { name: 'Delete "First"?' })).toBeInTheDocument();

    await user.click(within(rowOf('Second')).getByRole('button', { name: 'Open' }));
    expect(screen.getAllByRole('group')).toHaveLength(1);
    expect(screen.getByRole('group', { name: REPLACE })).toBeInTheDocument();

    await user.click(within(rowOf('First')).getByRole('button', { name: 'Delete' }));
    expect(screen.getAllByRole('group')).toHaveLength(1);
    await user.click(sizeBtn);
    expect(screen.getAllByRole('group')).toHaveLength(1);
    expect(screen.getByRole('group', { name: REPLACE })).toBeInTheDocument();
  });

  it('Open saved is disabled while editing is paused (D1)', async () => {
    await setupOpen({ editingPaused: true });
    expect(screen.getByRole('button', { name: 'Open saved' })).toBeDisabled();
  });

  it('a list already shown has its Open and Delete disabled when editing becomes paused', async () => {
    const { user, rerender } = await setupOpen();
    await showList(user);
    rerender(<GridPanel grid={makeGrid()} gridSize={SIZE} selectedCell={null} symmetryEnabled editingPaused onToggleBlack={vi.fn()} onNewGrid={vi.fn()} onOpenSaved={vi.fn()} />);
    for (const name of ['Open', 'Delete']) {
      for (const b of screen.getAllByRole('button', { name })) expect(b).toBeDisabled();
    }
  });
});
