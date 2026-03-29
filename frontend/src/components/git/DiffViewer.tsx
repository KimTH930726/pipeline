interface Props {
  diffText: string;
  filePath: string;
}

export default function DiffViewer({ diffText, filePath }: Props) {
  if (!diffText) {
    return <p className="text-sm text-gray-400 p-4">파일을 선택하면 diff가 표시됩니다.</p>;
  }

  const lines = diffText.split('\n');

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-100 px-4 py-2 text-sm font-mono text-gray-600 border-b">
        {filePath}
      </div>
      <pre className="text-xs font-mono overflow-auto max-h-[500px] p-0 m-0">
        {lines.map((line, i) => {
          let bg = '';
          if (line.startsWith('+') && !line.startsWith('+++')) bg = 'bg-green-50 text-green-800';
          else if (line.startsWith('-') && !line.startsWith('---')) bg = 'bg-red-50 text-red-800';
          else if (line.startsWith('@@')) bg = 'bg-blue-50 text-blue-600';

          return (
            <div key={i} className={`px-4 py-0.5 ${bg}`}>
              {line || ' '}
            </div>
          );
        })}
      </pre>
    </div>
  );
}
