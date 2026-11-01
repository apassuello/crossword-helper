/**
 * Tests for ExportPanel - grid export functionality
 * Tests format selection (JSON, HTML, Text), preview, export button
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ExportPanel from '../../components/ExportPanel';
import { completedGrid } from '../fixtures/gridFixtures';
import { captureDownloads, readBlob } from '../importExportHelpers';

// Mock ProgressIndicator
vi.mock('../../components/ProgressIndicator', () => ({
  default: ({ message }) => <div data-testid="progress-indicator">{message}</div>,
}));

describe('ExportPanel Component', () => {
  const defaultProps = {
    grid: completedGrid,
    gridSize: 11,
    numbering: {},
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders export format selector', () => {
    render(<ExportPanel {...defaultProps} />);
    expect(screen.getByLabelText(/export format/i)).toBeInTheDocument();
  });

  it('shows JSON export option', () => {
    render(<ExportPanel {...defaultProps} />);
    const formatSelect = screen.getByLabelText(/export format/i);
    expect(formatSelect).toHaveTextContent(/JSON/i);
  });

  it('shows HTML export option', () => {
    render(<ExportPanel {...defaultProps} />);
    const formatSelect = screen.getByLabelText(/export format/i);
    expect(formatSelect).toHaveTextContent(/HTML/i);
  });

  it('shows Text export option', () => {
    render(<ExportPanel {...defaultProps} />);
    const formatSelect = screen.getByLabelText(/export format/i);
    expect(formatSelect).toHaveTextContent(/Text/i);
  });

  // novice-readiness spec 0.2.7 §3.1 (G10): unfinished formats and the disabled checkbox are not rendered.
  it('does not render the PDF, .puz or Include-clues controls', () => {
    render(<ExportPanel {...defaultProps} />);
    expect(screen.queryByText('PDF (coming soon)')).toBeNull();
    expect(screen.queryByText('.puz (coming soon)')).toBeNull();
    expect(screen.queryByText('Include clues (if available)')).toBeNull();
    expect(screen.queryByRole('checkbox')).toBeNull();
    const terms = Array.from(document.querySelectorAll('dt')).map((el) => el.textContent);
    expect(terms).not.toContain('PDF');
    expect(terms).not.toContain('.puz');
  });

  it('keeps the JSON, HTML and Text options and Format Information terms', () => {
    render(<ExportPanel {...defaultProps} />);
    const options = Array.from(document.querySelectorAll('option')).map((el) => el.textContent);
    expect(options).toEqual([
      expect.stringMatching(/JSON/),
      expect.stringMatching(/HTML/),
      expect.stringMatching(/Text/),
    ]);
    const terms = Array.from(document.querySelectorAll('dt')).map((el) => el.textContent);
    expect(terms).toEqual(['JSON', 'HTML', 'Text']);
  });

  it('generates preview when Preview button is clicked', async () => {
    const user = userEvent.setup();
    render(<ExportPanel {...defaultProps} />);

    // Click the Preview button
    const previewButton = screen.getByRole('button', { name: /preview/i });
    await user.click(previewButton);

    await waitFor(() => {
      // A <pre> with preview content should appear
      const previewContent = document.querySelector('.preview-content');
      expect(previewContent).toBeTruthy();
      expect(previewContent.textContent.length).toBeGreaterThan(0);
    });
  });

  it('has an enabled Export button', () => {
    render(<ExportPanel {...defaultProps} />);
    const exportButton = screen.getByRole('button', { name: /^export$/i });
    expect(exportButton).toBeEnabled();
  });

  it('triggers export on Export button click', async () => {
    const user = userEvent.setup();

    // Mock URL.createObjectURL and URL.revokeObjectURL (not available in jsdom)
    const mockUrl = 'blob:http://localhost/fake-blob-url';
    global.URL.createObjectURL = vi.fn(() => mockUrl);
    global.URL.revokeObjectURL = vi.fn();

    // Spy on link click — use the native prototype method to avoid recursion
    const clickSpy = vi.fn();
    const realCreateElement = Document.prototype.createElement.bind(document);
    const createElementSpy = vi.spyOn(document, 'createElement');
    createElementSpy.mockImplementation((tag, options) => {
      const el = realCreateElement(tag, options);
      if (tag === 'a') {
        el.click = clickSpy;
      }
      return el;
    });

    render(<ExportPanel {...defaultProps} />);

    const exportButton = screen.getByRole('button', { name: /^export$/i });
    await user.click(exportButton);

    // The component uses setTimeout(500ms) before downloading
    await waitFor(() => {
      expect(clickSpy).toHaveBeenCalled();
    }, { timeout: 2000 });

    createElementSpy.mockRestore();
    delete global.URL.createObjectURL;
    delete global.URL.revokeObjectURL;
  });
});

// Task 9 (clue-authoring spec 0.1.4, section 3.5 "Grid JSON file, browser export"): the JSON file always
// writes `clues` (`{}` when there are none), and the JSON preview shows what the file holds.
describe('ExportPanel clues (spec 3.5 browser export)', () => {
  const MAP = {
    '0,0,across': { text: 'Feline', answer: 'CAT??????' },
    '2,3,down': { text: 'Sea bird', answer: '?GULL' },
  };
  const props = { grid: completedGrid, gridSize: 11, numbering: {} };
  let downloads;

  beforeEach(() => {
    downloads = captureDownloads();
  });
  afterEach(() => downloads.restore());

  const exportedFile = async (user) => {
    await user.click(screen.getByRole('button', { name: /^export$/i }));
    await waitFor(() => expect(downloads.blobs).toHaveLength(1), { timeout: 2000 });
    return JSON.parse(await readBlob(downloads.blobs[0]));
  };
  const previewText = async (user) => {
    await user.click(screen.getByRole('button', { name: /preview/i }));
    return document.querySelector('.preview-content').textContent;
  };

  it('the JSON download carries `clues` equal to the clues prop', async () => {
    const user = userEvent.setup();
    render(<ExportPanel {...props} clues={MAP} />);
    const file = await exportedFile(user);
    expect(file.clues).toStrictEqual(MAP);
  });

  it('the JSON download carries `clues` of {} when the prop is {}', async () => {
    const user = userEvent.setup();
    render(<ExportPanel {...props} clues={{}} />);
    const file = await exportedFile(user);
    expect('clues' in file).toBe(true);
    expect(file.clues).toStrictEqual({});
  });

  it('the JSON preview shows the same object as the file, clues included', async () => {
    const user = userEvent.setup();
    render(<ExportPanel {...props} clues={MAP} />);
    const shown = JSON.parse(await previewText(user));
    expect(shown.clues).toStrictEqual(MAP);
    expect(shown).toStrictEqual(await exportedFile(user));
  });

  it('the JSON preview shows `clues` of {} when the prop is {}', async () => {
    const user = userEvent.setup();
    render(<ExportPanel {...props} clues={{}} />);
    const shown = JSON.parse(await previewText(user));
    expect('clues' in shown).toBe(true);
    expect(shown.clues).toStrictEqual({});
  });
});
