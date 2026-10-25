/**
 * Test setup file for Vitest + React Testing Library
 *
 * This file runs before all tests and sets up:
 * - jest-dom matchers for DOM assertions
 * - Mock Service Worker (MSW) for API mocking
 * - Global test utilities
 * - Mock EventSource for SSE testing
 */

import '@testing-library/jest-dom';
import { act, cleanup } from '@testing-library/react';
import { configure } from '@testing-library/dom';
import { afterEach, beforeAll, afterAll, vi } from 'vitest';
import { server } from './fixtures/apiMocks';

// @testing-library/react 14 bundles its own @testing-library/dom (9.x), so the dom copy that
// user-event drives (10.x, top level) never gets React's act() event wrapper, and every
// `user.click` that sets state printed "not wrapped in act(...)". Install the wrapper on
// that copy. (Awaiting the resolution in a test cannot fix this: the update is the click's.)
configure({ eventWrapper: (cb) => { let r; act(() => { r = cb(); }); return r; } });

// Establish API mocking before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests
afterEach(() => {
  server.resetHandlers();
  cleanup(); // Cleanup React Testing Library after each test
});

// Clean up after the tests are finished
afterAll(() => server.close());

// Mock EventSource for SSE testing
class MockEventSource {
  constructor(url) {
    this.url = url;
    this.readyState = 1; // OPEN
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;

    // Store instance for test control
    MockEventSource.instances.push(this);

    // Simulate immediate connection
    setTimeout(() => {
      if (this.onopen) {
        this.onopen({ type: 'open' });
      }
    }, 0);
  }

  close() {
    this.readyState = 2; // CLOSED
  }

  // Test helper: simulate receiving a message
  static sendMessage(data) {
    MockEventSource.instances.forEach(instance => {
      if (instance.onmessage) {
        instance.onmessage({
          data: typeof data === 'string' ? data : JSON.stringify(data)
        });
      }
    });
  }

  // Test helper: simulate error
  static sendError(error) {
    MockEventSource.instances.forEach(instance => {
      if (instance.onerror) {
        instance.onerror(error || { type: 'error' });
      }
    });
  }

  // Test helper: clear all instances
  static clearInstances() {
    MockEventSource.instances = [];
  }
}

MockEventSource.instances = [];

global.EventSource = MockEventSource;

// Clean up EventSource instances after each test
afterEach(() => {
  MockEventSource.clearInstances();
});

// Mock window.matchMedia (for responsive components)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
global.localStorage = localStorageMock;

// Reset localStorage mocks after each test
afterEach(() => {
  localStorageMock.getItem.mockClear();
  localStorageMock.setItem.mockClear();
  localStorageMock.removeItem.mockClear();
  localStorageMock.clear.mockClear();
});

// jsdom does not implement scrollIntoView; PatternMatcher calls it when results arrive
// (novice-readiness spec 0.2.15 §4 item 2, SR2). Tests that assert on it install a spy.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
