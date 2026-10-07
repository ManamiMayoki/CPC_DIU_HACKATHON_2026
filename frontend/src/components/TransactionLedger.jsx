import { useState } from 'react';
import { Search, FileText, ArrowRight } from 'lucide-react';

export default function TransactionLedger({ 
  transactions = [], 
  onInvestigateAccount 
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [minAmount, setMinAmount] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Filter transactions
  const filtered = transactions.filter((tx) => {
    const q = searchTerm.toLowerCase();
    const matchesSearch = !q || 
      tx.transaction_id?.toLowerCase().includes(q) ||
      tx.sender_id?.toLowerCase().includes(q) ||
      tx.receiver_id?.toLowerCase().includes(q);

    const matchesAmount = !minAmount || (tx.amount >= Number(minAmount));
    return matchesSearch && matchesAmount;
  });

  const totalPages = Math.ceil(filtered.length / pageSize) || 1;
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

  return (
    <section style={{ maxWidth: '1440px', margin: '0 auto', padding: '36px 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            color: 'var(--primary-neon)',
            fontSize: '0.74rem',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: '6px'
          }}>
            <FileText size={14} color="#B8FF3D" />
            <span>TRANSACTION REPOSITORY</span>
          </div>
          <h2 style={{ fontSize: '2rem', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
            Transaction Ledger
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px' }}>
            Validated transactions with directed edges, amounts, timestamps, and account endpoints.
          </p>
        </div>

        {/* Filter Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Search Tx ID, Sender, Receiver..."
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
              className="input-fintech"
              style={{ width: '240px', padding: '7px 14px 7px 34px', fontSize: '0.82rem', fontFamily: 'var(--font-mono)' }}
            />
          </div>

          <input
            type="number"
            placeholder="Min Amount (BDT)"
            value={minAmount}
            onChange={(e) => { setMinAmount(e.target.value); setPage(1); }}
            className="input-fintech"
            style={{ width: '130px', padding: '7px 14px', fontSize: '0.82rem', fontFamily: 'var(--font-mono)' }}
          />
        </div>
      </div>

      {/* Table Container */}
      <div className="glass-panel" style={{ borderRadius: '18px', overflow: 'hidden', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: 'rgba(255, 255, 255, 0.03)', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>TX ID</th>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>SENDER</th>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>DIRECTION</th>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>RECEIVER</th>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>AMOUNT (BDT)</th>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>TIMESTAMP</th>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textAlign: 'right' }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {paginated.map((tx, idx) => (
              <tr
                key={tx.transaction_id || idx}
                style={{
                  borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                  transition: 'background 0.15s ease'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                {/* Tx ID */}
                <td style={{ padding: '14px 20px', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#94A3B8' }}>
                  {tx.transaction_id}
                </td>

                {/* Sender */}
                <td style={{ padding: '14px 20px' }}>
                  <button
                    onClick={() => onInvestigateAccount && onInvestigateAccount(tx.sender_id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#FFFFFF',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 600,
                      fontSize: '0.88rem',
                      cursor: 'pointer',
                      padding: 0,
                      textAlign: 'left'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.color = 'var(--primary-neon)'}
                    onMouseLeave={(e) => e.currentTarget.style.color = '#FFFFFF'}
                  >
                    {tx.sender_id}
                  </button>
                </td>

                {/* Direction Icon */}
                <td style={{ padding: '14px 20px' }}>
                  <ArrowRight size={14} color="#B8FF3D" />
                </td>

                {/* Receiver */}
                <td style={{ padding: '14px 20px' }}>
                  <button
                    onClick={() => onInvestigateAccount && onInvestigateAccount(tx.receiver_id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#FFFFFF',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 600,
                      fontSize: '0.88rem',
                      cursor: 'pointer',
                      padding: 0,
                      textAlign: 'left'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.color = 'var(--primary-neon)'}
                    onMouseLeave={(e) => e.currentTarget.style.color = '#FFFFFF'}
                  >
                    {tx.receiver_id}
                  </button>
                </td>

                {/* Amount */}
                <td style={{ padding: '14px 20px', fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.95rem', color: '#FFFFFF' }}>
                  ৳{Number(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>

                {/* Timestamp */}
                <td style={{ padding: '14px 20px', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {tx.timestamp}
                </td>

                {/* Action */}
                <td style={{ padding: '14px 20px', textAlign: 'right' }}>
                  <button
                    onClick={() => onInvestigateAccount && onInvestigateAccount(tx.sender_id)}
                    className="btn-icon"
                    style={{ padding: '6px 10px', fontSize: '0.74rem' }}
                    title="Follow Sender"
                  >
                    <ArrowRight size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination Bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 20px',
          background: 'rgba(255, 255, 255, 0.02)',
          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
          fontFamily: 'var(--font-mono)'
        }}>
          <div>
            Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, filtered.length)} of {filtered.length} transactions
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              disabled={page <= 1}
              onClick={() => setPage(p => Math.max(1, p - 1))}
              className="btn-secondary"
              style={{ padding: '5px 12px', fontSize: '0.76rem', opacity: page <= 1 ? 0.4 : 1 }}
            >
              Previous
            </button>
            <span>Page {page} of {totalPages}</span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              className="btn-secondary"
              style={{ padding: '5px 12px', fontSize: '0.76rem', opacity: page >= totalPages ? 0.4 : 1 }}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
