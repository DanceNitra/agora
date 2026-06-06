import React, { useState, useEffect, useCallback, useRef } from 'react';

export interface Shortcut {
  key: string;
  label: string;
  description: string;
  action: () => void;
}

interface CommandPaletteProps {
  shortcuts: Shortcut[];
  isOpen: boolean;
  onClose: () => void;
}

const CommandPalette: React.FC<CommandPaletteProps> = ({
  shortcuts,
  isOpen,
  onClose,
}) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = query.trim()
    ? shortcuts.filter(
        (s) =>
          s.label.toLowerCase().includes(query.toLowerCase()) ||
          s.description.toLowerCase().includes(query.toLowerCase()),
      )
    : shortcuts;

  // Reset when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Handle clamp selected index
  useEffect(() => {
    if (selectedIndex >= filtered.length) {
      setSelectedIndex(Math.max(0, filtered.length - 1));
    }
  }, [filtered.length, selectedIndex]);

  const execute = useCallback(
    (shortcut: Shortcut) => {
      shortcut.action();
      onClose();
    },
    [onClose],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < filtered.length - 1 ? prev + 1 : 0,
        );
        return;
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : filtered.length - 1,
        );
        return;
      }

      if (e.key === 'Enter') {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          execute(filtered[selectedIndex]);
        }
        return;
      }
    },
    [filtered, selectedIndex, execute, onClose],
  );

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div style={styles.backdrop} onClick={onClose} />

      {/* Palette */}
      <div style={styles.palette}>
        <div style={styles.inputRow}>
          <span style={styles.searchIcon}>⌕</span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search commands…"
            style={styles.input}
          />
          <span style={styles.escHint}>ESC</span>
        </div>

        <div style={styles.list}>
          {filtered.length === 0 && (
            <div style={styles.empty}>No matching commands.</div>
          )}
          {filtered.map((shortcut, idx) => (
            <div
              key={shortcut.key}
              style={{
                ...styles.item,
                background:
                  idx === selectedIndex
                    ? 'rgba(251,191,36,0.15)'
                    : 'transparent',
              }}
              onMouseEnter={() => setSelectedIndex(idx)}
              onMouseDown={(e) => {
                e.preventDefault();
                execute(shortcut);
              }}
            >
              <div style={styles.itemLeft}>
                <kbd style={styles.kbd}>{shortcut.key}</kbd>
                <span style={styles.itemLabel}>{shortcut.label}</span>
              </div>
              <span style={styles.itemDesc}>{shortcut.description}</span>
            </div>
          ))}
        </div>

        {/* Footer hints */}
        <div style={styles.footer}>
          <span>↑↓ Navigate</span>
          <span>↵ Select</span>
          <span>⎋ Close</span>
        </div>
      </div>
    </>
  );
};

const styles: Record<string, React.CSSProperties> = {
  backdrop: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.5)',
    zIndex: 999,
  },
  palette: {
    position: 'fixed',
    top: '15%',
    left: '50%',
    transform: 'translateX(-50%)',
    width: '520px',
    maxWidth: '90vw',
    background: '#2a2a2a',
    border: '1px solid #3a3a3a',
    borderRadius: '10px',
    boxShadow: '0 8px 40px rgba(0,0,0,0.6)',
    zIndex: 1000,
    overflow: 'hidden',
    fontFamily: "'Inter', system-ui, sans-serif",
  },
  inputRow: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px 14px',
    borderBottom: '1px solid #3a3a3a',
    gap: '8px',
  },
  searchIcon: {
    color: '#6b7280',
    fontSize: '18px',
  },
  input: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: '#d4d4d4',
    fontSize: '15px',
    fontFamily: 'inherit',
  },
  escHint: {
    color: '#525252',
    fontSize: '11px',
    fontFamily: 'monospace',
  },
  list: {
    maxHeight: '300px',
    overflowY: 'auto',
    padding: '4px 0',
  },
  empty: {
    textAlign: 'center',
    padding: '20px',
    color: '#525252',
    fontSize: '14px',
  },
  item: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 14px',
    cursor: 'pointer',
    transition: 'background 0.1s',
  },
  itemLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  kbd: {
    display: 'inline-block',
    padding: '2px 6px',
    background: '#3a3a3a',
    borderRadius: '4px',
    fontSize: '11px',
    color: '#fbbf24',
    fontFamily: 'monospace',
    minWidth: 28,
    textAlign: 'center',
  },
  itemLabel: {
    fontSize: '14px',
    color: '#d4d4d4',
    fontWeight: 500,
  },
  itemDesc: {
    fontSize: '12px',
    color: '#6b7280',
    flexShrink: 0,
    marginLeft: '12px',
  },
  footer: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    padding: '8px 14px',
    borderTop: '1px solid #3a3a3a',
    fontSize: '11px',
    color: '#525252',
  },
};

export default CommandPalette;
