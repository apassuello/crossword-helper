/**
 * Shared helpers for the Task 9 tests (clue-authoring spec 0.1.4, section 3.5: grid-file import and
 * export with clues). Not a test file.
 *
 * `api.checkClues` is installed by assignment, never `vi.spyOn`: a spy on a method that does not
 * exist throws. `stubCheckClues` returns a restore function that puts back whatever the client had
 * (nothing at RED, the real method after GREEN), so other tests never see the stub.
 */
import { vi } from 'vitest';
import { api } from '../api/client';

export const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

/** Replace `api.checkClues` with a `vi.fn`. Returns `{ fn, restore }`. */
export function stubCheckClues(impl) {
  const original = Object.getOwnPropertyDescriptor(api, 'checkClues');
  const fn = vi.fn(impl);
  api.checkClues = fn;
  const restore = () => {
    if (original) Object.defineProperty(api, 'checkClues', original);
    else delete api.checkClues;
  };
  return { fn, restore };
}

/** Read a Blob's text (jsdom's Blob has no `.text()`). */
export const readBlob = (blob) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });

/**
 * Capture what the export panel downloads. `createObjectURL` is not in jsdom, so it is installed here;
 * the anchor click is a no-op. Returns `{ blobs, restore }`.
 */
export function captureDownloads() {
  const origCreate = global.URL.createObjectURL;
  const origRevoke = global.URL.revokeObjectURL;
  const blobs = [];
  global.URL.createObjectURL = vi.fn((blob) => {
    blobs.push(blob);
    return 'blob:http://localhost/captured';
  });
  global.URL.revokeObjectURL = vi.fn();
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  return {
    blobs,
    restore: () => {
      click.mockRestore();
      if (origCreate) global.URL.createObjectURL = origCreate;
      else delete global.URL.createObjectURL;
      if (origRevoke) global.URL.revokeObjectURL = origRevoke;
      else delete global.URL.revokeObjectURL;
    },
  };
}
