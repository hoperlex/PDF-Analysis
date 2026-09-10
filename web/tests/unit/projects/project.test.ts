/**
 * Project name bounds, and the difference between "no documents" and "the server did not
 * say how many".
 */

import { describe, expect, it } from 'vitest';

import type { Project } from '@/shared/api';
import { PROJECT_UID_PATTERN } from '@/shared/api';
import {
  PROJECT_NAME_MAX_LENGTH,
  PROJECT_NAME_MIN_LENGTH,
  UNKNOWN_COUNT_LABEL,
  looksLikeProjectUid,
  projectDocumentCount,
  projectDocumentCountLabel,
  projectNameProblemMessage,
  validateProjectName,
} from '@/entities/project';
import { CONTRACT_PATH, readJson } from '../../guards/lib/repo';

interface ContractDocument {
  readonly components: {
    readonly schemas: Record<
      string,
      { readonly properties?: Record<string, { minLength?: number; maxLength?: number }> }
    >;
  };
}

const document = readJson<ContractDocument>(CONTRACT_PATH);

describe('the name bounds are the contract bounds', () => {
  it('matches CreateProjectRequest.name in the contract document', () => {
    const name = document.components.schemas['CreateProjectRequest']?.properties?.['name'];
    expect(name?.minLength).toBe(PROJECT_NAME_MIN_LENGTH);
    expect(name?.maxLength).toBe(PROJECT_NAME_MAX_LENGTH);
  });
});

describe('a name is checked before a request is spent on it', () => {
  it('refuses an empty or whitespace-only name', () => {
    expect(validateProjectName('')).toBe('empty');
    expect(validateProjectName('   ')).toBe('empty');
  });

  it('accepts a name at the bound and refuses one character more', () => {
    expect(validateProjectName('a'.repeat(PROJECT_NAME_MAX_LENGTH))).toBeNull();
    expect(validateProjectName('a'.repeat(PROJECT_NAME_MAX_LENGTH + 1))).toBe('too_long');
  });

  it('accepts an ordinary name', () => {
    expect(validateProjectName('  Annual report 2024  ')).toBeNull();
  });

  it('has a message for every problem', () => {
    expect(projectNameProblemMessage('empty').length).toBeGreaterThan(0);
    expect(projectNameProblemMessage('too_long')).toContain(String(PROJECT_NAME_MAX_LENGTH));
  });
});

describe('an absent document count is unknown, not zero', () => {
  const base: Project = {
    project_uid: 'prj_01M2545JSD15ETSNNV904X991J',
    name: 'AR 2024',
    created_at: '2026-01-01T00:00:00Z',
  };

  it('reports null when the response carried no count', () => {
    expect(projectDocumentCount(base)).toBeNull();
    expect(projectDocumentCountLabel(base)).toBe(UNKNOWN_COUNT_LABEL);
    expect(projectDocumentCountLabel(base)).not.toBe('0');
  });

  it('reports zero when the response actually said zero', () => {
    expect(projectDocumentCount({ ...base, document_count: 0 })).toBe(0);
    expect(projectDocumentCountLabel({ ...base, document_count: 0 })).toBe('0');
  });

  it('reports the count when there is one', () => {
    expect(projectDocumentCountLabel({ ...base, document_count: 3 })).toBe('3');
  });
});

describe('a project address is recognised by shape only', () => {
  it('accepts the contract shape and refuses anything else', () => {
    expect(looksLikeProjectUid('prj_01M2545JSD15ETSNNV904X991J')).toBe(true);
    expect(looksLikeProjectUid('run_01M2545JSD15ETSNNV904X991J')).toBe(false);
    expect(looksLikeProjectUid('prj_lowercase')).toBe(false);
    expect(looksLikeProjectUid('')).toBe(false);
  });

  it('uses the generated pattern rather than a copied regular expression', () => {
    expect(PROJECT_UID_PATTERN).toBe('^prj_[0-9A-HJKMNP-TV-Z]{26}$');
  });
});
