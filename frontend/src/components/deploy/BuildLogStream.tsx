import { useEffect, useRef } from 'react';

interface Props {
  lines: string[];
}

export default function BuildLogStream({ lines }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines]);

  return (
    <div className="bg-gray-900 rounded-lg p-4 font-mono text-xs text-gray-300 max-h-[400px] overflow-auto">
      {lines.length === 0 ? (
        <p className="text-gray-500">빌드 로그를 기다리는 중...</p>
      ) : (
        lines.map((line, i) => {
          let color = 'text-gray-300';
          if (line.includes('[ERROR]') || line.includes('Error')) color = 'text-red-400';
          else if (line.includes('[BUILD]')) color = 'text-green-400';
          else if (line.includes('FAILED')) color = 'text-red-500 font-bold';

          return (
            <div key={i} className={color}>
              {line}
            </div>
          );
        })
      )}
      <div ref={endRef} />
    </div>
  );
}
