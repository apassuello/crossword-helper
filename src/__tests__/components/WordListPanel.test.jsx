/**
 * WordListPanel upload flow: no extension gate, dry-run preview, confirm/cancel,
 * and 400 reasons (spec 2026-10-22-basics-first O6, O8, O9).
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import WordListPanel from '../../components/WordListPanel';
import { api, ApiError } from '../../api/client';

// jsdom's Blob has no text(); real browsers do, and the component relies on it.
if (typeof Blob.prototype.text !== 'function') {
  Blob.prototype.text = function text() {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(r.result);
      r.onerror = reject;
      r.readAsText(this);
    });
  };
}

const LIST_RESPONSE = { wordlists: [], categories: {}, tags: {} };

const parsed = (n) =>
  Array.from({ length: n }, (_, i) => ({ word: `WORD${String.fromCharCode(65 + (i % 26))}${i}`, score: 50 + i }));

async function openUploadAndPick(user, file, name) {
  render(<WordListPanel />);
  await waitFor(() => expect(api.getWordlists).toHaveBeenCalled());
  await user.click(await screen.findByRole('button', { name: /upload wordlist/i }));
  const input = document.querySelector('input[type="file"]');
  await user.upload(input, file, { applyAccept: false });
  if (name) {
    const nameBox = screen.getByPlaceholderText(/name for this wordlist/i);
    await user.clear(nameBox);
    await user.type(nameBox, name);
  }
}

describe('WordListPanel upload', () => {
  beforeEach(() => {
    vi.spyOn(api, 'getWordlists').mockResolvedValue(LIST_RESPONSE);
    vi.spyOn(api, 'getWordlist').mockResolvedValue({
      metadata: { name: 'nexus', category: 'custom', description: '' },
      words: ['AAA'],
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it('does not restrict the file input by extension', async () => {
    render(<WordListPanel />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: /upload wordlist/i }));
    const input = document.querySelector('input[type="file"]');
    expect(input.hasAttribute('accept')).toBe(false);
    expect(screen.queryByText(/\.txt/)).not.toBeInTheDocument();
  });

  it('a .dict file reaches the dry-run call and name auto-fill strips its extension', async () => {
    const spy = vi.spyOn(api, 'importWordlist').mockResolvedValue({
      words: parsed(2),
      skipped: [],
    });
    const user = userEvent.setup();
    const file = new File(['CAT;50\nDOG;40'], 'nexus.dict', { type: '' });
    await openUploadAndPick(user, file);
    expect(screen.getByPlaceholderText(/name for this wordlist/i)).toHaveValue('nexus');
    await user.click(screen.getByRole('button', { name: /^upload$/i }));
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    expect(spy.mock.calls[0][0]).toMatchObject({
      name: 'nexus',
      content: 'CAT;50\nDOG;40',
      dryRun: true,
    });
  });

  it('shows totals, skipped reasons, first 20 words with scores, Confirm and Cancel', async () => {
    vi.spyOn(api, 'importWordlist').mockResolvedValue({
      words: parsed(25),
      skipped: [
        { line: 3, text: 'a', reason: 'too short' },
        { line: 4, text: 'b', reason: 'too short' },
        { line: 5, text: 'c1', reason: 'bad score' },
      ],
    });
    const user = userEvent.setup();
    await openUploadAndPick(user, new File(['x'], 'l.dict'));
    await user.click(screen.getByRole('button', { name: /^upload$/i }));
    const preview = await screen.findByTestId('upload-preview');
    expect(within(preview).getByText(/25 valid words/i)).toBeInTheDocument();
    expect(within(preview).getByText(/3 skipped/i)).toBeInTheDocument();
    expect(within(preview).getByText(/too short/)).toBeInTheDocument();
    expect(within(preview).getByText(/bad score/)).toBeInTheDocument();
    expect(within(preview).getAllByTestId('preview-word')).toHaveLength(20);
    expect(within(preview).getByText('WORDA0')).toBeInTheDocument();
    expect(within(preview).getByText('50')).toBeInTheDocument();
    expect(within(preview).getByRole('button', { name: /confirm/i })).toBeInTheDocument();
    expect(within(preview).getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('Confirm sends the real import (dryRun false) after the dry run', async () => {
    const spy = vi
      .spyOn(api, 'importWordlist')
      .mockResolvedValueOnce({ words: parsed(2), skipped: [] })
      .mockResolvedValueOnce({ name: 'nexus' });
    const user = userEvent.setup();
    await openUploadAndPick(user, new File(['CAT\nDOG'], 'nexus.dict'));
    await user.click(screen.getByRole('button', { name: /^upload$/i }));
    const preview = await screen.findByTestId('upload-preview');
    await user.click(within(preview).getByRole('button', { name: /confirm/i }));
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
    expect(spy.mock.calls[1][0]).toMatchObject({ name: 'nexus', content: 'CAT\nDOG', category: 'custom' });
    expect(spy.mock.calls[1][0].dryRun).toBeFalsy();
    await waitFor(() => expect(api.getWordlist).toHaveBeenCalledWith('nexus', expect.anything()));
  });

  it('Cancel in the preview sends one request in total', async () => {
    const spy = vi.spyOn(api, 'importWordlist').mockResolvedValue({ words: parsed(2), skipped: [] });
    const user = userEvent.setup();
    await openUploadAndPick(user, new File(['CAT\nDOG'], 'nexus.dict'));
    await user.click(screen.getByRole('button', { name: /^upload$/i }));
    const preview = await screen.findByTestId('upload-preview');
    await user.click(within(preview).getByRole('button', { name: /cancel/i }));
    expect(screen.queryByTestId('upload-preview')).not.toBeInTheDocument();
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it('a 400 renders the error, skipped count and reasons, with no preview', async () => {
    const spy = vi.spyOn(api, 'importWordlist').mockRejectedValue(
      new ApiError({
        status: 400,
        code: 'HTTP_400',
        message: 'No valid words found',
        details: { skipped: 4, reasons: { 'too short': 3, 'bad score': 1 } },
      })
    );
    const user = userEvent.setup();
    await openUploadAndPick(user, new File(['a\nb'], 'x.dict'), 'x');
    await user.click(screen.getByRole('button', { name: /^upload$/i }));
    expect(await screen.findByText(/No valid words found/)).toBeInTheDocument();
    expect(screen.getByText(/4 skipped/i)).toBeInTheDocument();
    expect(screen.getByText(/too short/)).toBeInTheDocument();
    expect(screen.getByText(/bad score/)).toBeInTheDocument();
    expect(screen.queryByTestId('upload-preview')).not.toBeInTheDocument();
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it('a dry-run response for a file the user has since replaced is ignored', async () => {
    let resolveFirst;
    vi.spyOn(api, 'importWordlist').mockImplementationOnce(
      () => new Promise((resolve) => { resolveFirst = resolve; })
    );
    const user = userEvent.setup();
    await openUploadAndPick(user, new File(['OLD'], 'old.dict'), 'old');
    await user.click(screen.getByRole('button', { name: /^upload$/i }));
    await waitFor(() => expect(resolveFirst).toBeTypeOf('function'));
    await user.upload(document.querySelector('input[type="file"]'), new File(['NEW'], 'new.dict'), {
      applyAccept: false,
    });
    resolveFirst({ words: parsed(1), skipped: [] });
    await new Promise((r) => setTimeout(r, 0));
    expect(screen.queryByTestId('upload-preview')).not.toBeInTheDocument();
  });

  it('picking another file after a 400 clears the stale skipped-reasons box', async () => {
    vi.spyOn(api, 'importWordlist').mockRejectedValue(
      new ApiError({
        status: 400,
        code: 'HTTP_400',
        message: 'No valid words found',
        details: { skipped: 4, reasons: { 'too short': 4 } },
      })
    );
    const user = userEvent.setup();
    await openUploadAndPick(user, new File(['a\nb'], 'x.dict'), 'x');
    await user.click(screen.getByRole('button', { name: /^upload$/i }));
    expect(await screen.findByText(/4 skipped/i)).toBeInTheDocument();
    await user.upload(document.querySelector('input[type="file"]'), new File(['CAT'], 'y.dict'), {
      applyAccept: false,
    });
    expect(screen.queryByText(/4 skipped/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/too short/)).not.toBeInTheDocument();
  });
});
