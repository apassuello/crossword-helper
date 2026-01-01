/**
 * Tests for ExportPanel - grid export functionality
 * Tests format selection (JSON, HTML, Text), preview, download
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ExportPanel from '../../components/ExportPanel';
import { completedGrid } from '../fixtures/gridFixtures';

describe('ExportPanel Component', () => {
  const defaultProps = {
    grid: completedGrid,
    size: 11,
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

  it('generates preview when format selected', async () => {
    const user = userEvent.setup();
    render(<ExportPanel {...defaultProps} />);

    const formatSelect = screen.getByLabelText(/export format/i);
    await user.selectOptions(formatSelect, 'json');

    await waitFor(() => {
      expect(screen.getByText(/preview/i)).toBeInTheDocument();
    });
  });

  it('enables download button after preview generation', async () => {
    const user = userEvent.setup();
    render(<ExportPanel {...defaultProps} />);

    const formatSelect = screen.getByLabelText(/export format/i);
    await user.selectOptions(formatSelect, 'json');

    await waitFor(() => {
      const downloadButton = screen.getByRole('button', { name: /download/i });
      expect(downloadButton).toBeEnabled();
    });
  });

  it('triggers download on button click', async () => {
    const user = userEvent.setup();
    const createElementSpy = vi.spyOn(document, 'createElement');

    render(<ExportPanel {...defaultProps} />);

    const formatSelect = screen.getByLabelText(/export format/i);
    await user.selectOptions(formatSelect, 'json');

    const downloadButton = screen.getByRole('button', { name: /download/i });
    await user.click(downloadButton);

    expect(createElementSpy).toHaveBeenCalledWith('a');
  });
});
