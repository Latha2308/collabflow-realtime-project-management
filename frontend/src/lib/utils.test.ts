import { describe, it, expect } from 'vitest';
import { cn, formatDate, isOverdue } from './utils';

describe('utils', () => {
  describe('cn', () => {
    it('should merge class names correctly', () => {
      expect(cn('foo', 'bar')).toBe('foo bar');
    });

    it('should handle conditional classes', () => {
      // eslint-disable-next-line no-constant-binary-expression
      expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz');
    });

    it('should handle undefined and null', () => {
      expect(cn('foo', undefined, null, 'bar')).toBe('foo bar');
    });
  });

  describe('formatDate', () => {
    it('should format date correctly', () => {
      const date = '2026-11-23';
      const result = formatDate(date);
      expect(result).toMatch(/Nov 23, 2026/);
    });

    it('should handle invalid date', () => {
      const result = formatDate('invalid');
      expect(result).toBe('Invalid Date');
    });
  });

  describe('isOverdue', () => {
    it('should return true for past dates', () => {
      const pastDate = '2020-01-01';
      expect(isOverdue(pastDate)).toBe(true);
    });

    it('should return false for future dates', () => {
      const futureDate = '2030-01-01';
      expect(isOverdue(futureDate)).toBe(false);
    });
  });
});
