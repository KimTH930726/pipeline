import { useRef, useCallback, useMemo } from 'react';

interface Props {
  originalContent: string;
  resolvedContent: string;
}

function diffLines(original: string[], resolved: string[]) {
  const origSet = new Set(original);
  const resSet = new Set(resolved);
  const origHighlight = original.map((line) => !resSet.has(line));
  const resHighlight = resolved.map((line) => !origSet.has(line));
  return { origHighlight, resHighlight };
}

export default function ConflictDiffViewer({ originalContent, resolvedContent }: Props) {
  const leftRef = useRef<HTMLPreElement>(null);
  const rightRef = useRef<HTMLPreElement>(null);
  const syncing = useRef(false);

  const handleScroll = useCallback((source: 'left' | 'right') => {
    if (syncing.current) return;
    syncing.current = true;
    const from = source === 'left' ? leftRef.current : rightRef.current;
    const to = source === 'left' ? rightRef.current : leftRef.current;
    if (from && to) {
      to.scrollTop = from.scrollTop;
      to.scrollLeft = from.scrollLeft;
    }
    requestAnimationFrame(() => { syncing.current = false; });
  }, []);

  const origLines = useMemo(() => originalContent.split('\n'), [originalContent]);
  const resLines = useMemo(() => resolvedContent.split('\n'), [resolvedContent]);
  const { origHighlight, resHighlight } = useMemo(() => diffLines(origLines, resLines), [origLines, resLines]);

  const lineNumWidth = Math.max(origLines.length, resLines.length).toString().length * 0.6 + 1;

  return (
    <div className="grid grid-cols-2 gap-0">
      <div>
        <div className="px-3 py-1.5 bg-red-50 text-xs font-medium text-red-600 border-b flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-400 inline-block" />
          충돌 원본
        </div>
        <pre
          ref={leftRef}
          onScroll={() => handleScroll('left')}
          className="p-0 text-xs overflow-auto max-h-[400px] bg-gray-50 font-mono leading-5"
        >
          {origLines.map((line, i) => (
            <div
              key={i}
              className={`flex ${origHighlight[i] ? 'bg-red-100' : 'hover:bg-gray-100'}`}
            >
              <span
                className="text-gray-400 text-right pr-2 pl-2 select-none border-r border-gray-200 flex-shrink-0"
                style={{ minWidth: `${lineNumWidth}em` }}
              >
                {i + 1}
              </span>
              <span className={`pl-2 flex-1 whitespace-pre ${origHighlight[i] ? 'text-red-800' : 'text-gray-700'}`}>
                {line || ' '}
              </span>
            </div>
          ))}
        </pre>
      </div>
      <div>
        <div className="px-3 py-1.5 bg-green-50 text-xs font-medium text-green-600 border-b border-l flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-green-400 inline-block" />
          AI 해결안
        </div>
        <pre
          ref={rightRef}
          onScroll={() => handleScroll('right')}
          className="p-0 text-xs overflow-auto max-h-[400px] bg-gray-50 font-mono leading-5 border-l"
        >
          {resLines.map((line, i) => (
            <div
              key={i}
              className={`flex ${resHighlight[i] ? 'bg-green-100' : 'hover:bg-gray-100'}`}
            >
              <span
                className="text-gray-400 text-right pr-2 pl-2 select-none border-r border-gray-200 flex-shrink-0"
                style={{ minWidth: `${lineNumWidth}em` }}
              >
                {i + 1}
              </span>
              <span className={`pl-2 flex-1 whitespace-pre ${resHighlight[i] ? 'text-green-800' : 'text-gray-700'}`}>
                {line || ' '}
              </span>
            </div>
          ))}
        </pre>
      </div>
    </div>
  );
}
