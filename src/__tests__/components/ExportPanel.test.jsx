/**
 * Tests for ExportPanel - grid export functionality
 * Tests format selection (JSON, HTML, Text), preview, export button
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ExportPanel from '../../components/ExportPanel';
import { completedGrid } from '../fixtures/gridFixtures';

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
