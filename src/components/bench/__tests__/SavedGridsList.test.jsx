// novice-readiness spec 0.2.7 §3.4: the Open saved list (name, size, saved time; Open, Delete).
import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SavedGridsList from '../SavedGridsList';

const at = (d, h, m) => new Date(2026, 9, d, h, m).toISOString();
const ENTRIES = [
  { id: 'b', name: 'Newer', size: 21, savedAt: at(23, 18, 5) },
  { id: 'a', name: 'Older', size: 15, savedAt: at(22, 9, 30) },
];

const setup = (over = {}) => {
  const onOpen = vi.fn();
  const onDelete = vi.fn();
  render(<SavedGridsList entries={ENTRIES} disabled={false} onOpen={onOpen} onDelete={onDelete} {...over} />);
  return { onOpen, onDelete };
};

describe('SavedGridsList', () => {
  it('renders one row per entry in the given order, with name, size and local time', () => {
    setup();
    const rows = screen.getAllByRole('listitem');
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent('Newer');
    expect(rows[0]).toHaveTextContent('21×21');
    expect(rows[0]).toHaveTextContent('2026-10-23 18:05');
    expect(rows[1]).toHaveTextContent('Older');
    expect(rows[1]).toHaveTextContent('15×15');
    expect(rows[1]).toHaveTextContent('2026-10-22 09:30');
    for (const row of rows) {
      expect(within(row).getByRole('button', { name: 'Open' })).toBeInTheDocument();
      expect(within(row).getByRole('button', { name: 'Delete' })).toBeInTheDocument();
    }
  });

  it('an empty list shows no rows', () => {
    setup({ entries: [] });
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
  });

  it('Open hands the whole entry up; Delete hands up the id', async () => {
    const { onOpen, onDelete } = setup();
    const user = userEvent.setup();
    const rows = screen.getAllByRole('listitem');
    await user.click(within(rows[1]).getByRole('button', { name: 'Open' }));
    expect(onOpen).toHaveBeenCalledWith(ENTRIES[1]);
    await user.click(within(rows[0]).getByRole('button', { name: 'Delete' }));
    expect(onDelete).toHaveBeenCalledWith('b');
  });

  it('disabled disables every Open and Delete', () => {
    setup({ disabled: true });
    for (const b of screen.getAllByRole('button')) expect(b).toBeDisabled();
    expect(screen.getAllByRole('button')).toHaveLength(4);
  });
});
