// novice-readiness spec 0.2.8 §3.2 Import (Q2): the confirm's Replace is the only way to import
// over content, and it is disabled while editing is paused (D1).
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImportPanel from '../../components/ImportPanel';

const json = JSON.stringify({ size: 3, grid: [['C', 'A', 'T'], ['.', '.', '.'], ['.', '.', '.']] });

const openConfirm = async (props) => {
  const user = userEvent.setup();
  const onImport = vi.fn();
  const view = render(<ImportPanel onImport={onImport} currentGridSize={3} gridHasContent {...props} />);
  await user.click(screen.getByRole('button', { name: /paste json/i }));
  fireEvent.change(screen.getByLabelText(/paste json data/i), { target: { value: json } });
  await user.click(screen.getByRole('button', { name: /validate json/i }));
  await user.click(await screen.findByRole('button', { name: /import grid/i }));
  return { user, onImport, view };
};

describe('ImportPanel replace confirm', () => {
  it('Replace imports (control)', async () => {
    const { user, onImport } = await openConfirm();
    await user.click(screen.getByRole('button', { name: 'Replace' }));
    await vi.waitFor(() => expect(onImport).toHaveBeenCalledTimes(1), { timeout: 2000 });
  });

  it('Replace is disabled while editing is paused', async () => {
    const { view, onImport } = await openConfirm();
    view.rerender(
      <ImportPanel onImport={onImport} currentGridSize={3} gridHasContent editingPaused />
    );
    expect(screen.getByRole('button', { name: 'Replace' })).toBeDisabled();
  });
});
