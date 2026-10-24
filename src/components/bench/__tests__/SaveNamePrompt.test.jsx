/**
 * SaveNamePrompt: the name prompt under the Save button
 * (novice-readiness spec 0.2.7 §3.4 (G3), PD-6-G3, PD-6-G7, PD-6-G8).
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SaveNamePrompt from '../SaveNamePrompt';

const ENTRIES = [
  { id: 'own', name: 'Mine' },
  { id: 'x', name: 'Other' },
];

function setup(overrides = {}) {
  const props = {
    initialName: 'Mine',
    entries: ENTRIES,
    currentId: 'own',
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
    ...overrides,
  };
  render(<SaveNamePrompt {...props} />);
  return props;
}

const input = () => screen.getByRole('textbox');
const type = (value) => fireEvent.change(input(), { target: { value } });
const saveBtn = () => screen.getByRole('button', { name: 'Save' });

describe('SaveNamePrompt (§3.4 G3)', () => {
  it('is prefilled with initialName', () => {
    setup({ initialName: 'Mine' });
    expect(input()).toHaveValue('Mine');
  });

  it('confirms a trimmed name that no other entry has', () => {
    const props = setup();
    type('  Puzzle 1  ');
    fireEvent.click(saveBtn());
    expect(props.onConfirm).toHaveBeenCalledTimes(1);
    expect(props.onConfirm).toHaveBeenCalledWith('Puzzle 1');
    expect(screen.queryByRole('group')).toBeNull();
  });

  it.each([[''], ['   ']])('disables confirm for %j (PD-6-G7)', (value) => {
    const props = setup();
    type(value);
    expect(saveBtn()).toBeDisabled();
    fireEvent.click(saveBtn());
    expect(props.onConfirm).not.toHaveBeenCalled();
  });

  it('Cancel saves nothing and calls onCancel', () => {
    const props = setup();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(props.onCancel).toHaveBeenCalledTimes(1);
    expect(props.onConfirm).not.toHaveBeenCalled();
  });

  it("a different entry's name asks before replacing, then Replace passes its id (PD-6-G8)", () => {
    const props = setup();
    type('Other');
    fireEvent.click(saveBtn());
    expect(props.onConfirm).not.toHaveBeenCalled();
    expect(screen.getByText('Replace the saved grid named "Other"?')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Replace' }));
    expect(props.onConfirm).toHaveBeenCalledWith('Other', { replaceEntryId: 'x' });
  });

  it('Cancel in the collision confirm returns to the name field without saving', () => {
    const props = setup();
    type('Other');
    fireEvent.click(saveBtn());
    const group = screen.getByRole('group');
    fireEvent.click(group.querySelector('.xw-ghost-btn'));
    expect(screen.queryByRole('group')).toBeNull();
    expect(input()).toHaveValue('Other');
    expect(props.onConfirm).not.toHaveBeenCalled();
    expect(props.onCancel).not.toHaveBeenCalled();
  });

  it("the document's own current name is not a collision", () => {
    const props = setup({ initialName: 'Other', entries: [{ id: 'own', name: 'Other' }, { id: 'x', name: 'Zed' }] });
    type(' Other ');
    fireEvent.click(saveBtn());
    expect(screen.queryByRole('group')).toBeNull();
    expect(props.onConfirm).toHaveBeenCalledWith('Other');
  });

  it('collision matching is case-sensitive (PD-6-G3)', () => {
    const props = setup();
    type('other');
    fireEvent.click(saveBtn());
    expect(screen.queryByRole('group')).toBeNull();
    expect(props.onConfirm).toHaveBeenCalledWith('other');
  });
});
