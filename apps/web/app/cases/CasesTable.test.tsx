import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CasesTable } from './CasesTable';

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: any) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {}, // deprecated
    removeListener: () => {}, // deprecated
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

describe('CasesTable', () => {
  it('renders exact expected_recovery_paise from API', () => {
    const cases = [
      {
        id: 'CASE-123',
        created_at: new Date().toISOString(),
        amount_paise: 1000000,
        customer_segment: 'HIGH_VALUE',
        failure_type: 'INSUFFICIENT_FUNDS',
        risk_level: 'LOW',
        status: 'OPEN',
        expected_recovery_paise: 950000, // exact ML-derived value
      },
    ];

    render(<CasesTable initialCases={cases} />);
    
    // ₹9,500 = 950000 paise
    expect(screen.getByText('₹9,500')).toBeDefined();
  });

  it('renders Pending when expected_recovery_paise is null', () => {
    const cases = [
      {
        id: 'CASE-456',
        created_at: new Date().toISOString(),
        amount_paise: 2000000,
        customer_segment: 'MEDIUM_VALUE',
        failure_type: 'FRAUD_SUSPICION',
        risk_level: 'HIGH',
        status: 'ANALYZING',
        expected_recovery_paise: null, // missing ML value
      },
    ];

    render(<CasesTable initialCases={cases} />);
    
    expect(screen.getByText('Pending')).toBeDefined();
  });
});
